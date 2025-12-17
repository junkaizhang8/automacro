from typing import Callable
import itertools

from pynput.keyboard import Listener

from automacro.utils import _get_logger
from automacro.core import ThreadPool
from automacro.keyboard.key import Key, ModifierKey
from automacro.keyboard.key_sequence import KeySequence
from automacro.keyboard.normalize import normalize_char


class KeyListener:
    """
    A listener for character key presses.
    """

    def __init__(
        self,
        callbacks: dict[KeySequence, Callable[[], None]] | None = None,
        thread_pool: ThreadPool | None = None,
    ):
        """
        Initialize the key listener.

        Args:
            callbacks (dict[KeySequence, Callable[[], None] | None): Optional
            dictionary mapping keys to callback functions. Default is None.
            thread_pool (ThreadPool | None): Optional shared thread pool for
            executing callbacks. If None, callbacks will be executed in a
            single dedicated thread. Default is None.
        """

        self._init_callbacks(callbacks)

        self._listener = Listener(on_press=self._on_press, on_release=self._on_release)
        self._modifiers = set()
        self._keys_pressed = set()

        self._owns_thread_pool = thread_pool is None
        self._thread_pool = thread_pool or ThreadPool(1)

        self._logger = _get_logger(self.__class__)

    def __del__(self):
        try:
            if self._owns_thread_pool and self._thread_pool:
                # We don't wait for tasks to complete to avoid blocking
                self._thread_pool.shutdown(wait=False)
        except Exception as e:
            self._logger.error(f"Error shutting down thread pool: {e}")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_):
        self.stop()

    def _generate_modifier_subsets(self) -> list[set[ModifierKey]]:
        """
        Generate all possible subsets of modifier variant keys.

        Returns:
            list[set[ModifierKey]]: A list of sets, each containing a unique
            subset of modifier variant keys.
        """

        mods = {
            ModifierKey.CTRL_L,
            ModifierKey.CTRL_R,
            ModifierKey.ALT_L,
            ModifierKey.ALT_R,
            ModifierKey.CMD_L,
            ModifierKey.CMD_R,
            ModifierKey.SHIFT_L,
            ModifierKey.SHIFT_R,
        }

        subsets = []
        for r in range(len(mods) + 1):
            subsets.extend(set(p) for p in itertools.combinations(mods, r))
        return subsets

    def _normalize_modifiers(
        self, modifiers: frozenset[ModifierKey]
    ) -> list[set[ModifierKey]]:
        """
        Normalize a given set of modifiers by expanding any general modifier
        keys into their respective combinations and returning all possible unique
        combinations between left and right variants of the modifier keys. The
        combinations are generated using the Cartesian product of the expanded
        modifier sets.

        The Cartesian product is computed as P = C x M x D x S, where:
        - C is the set of CTRL variants (CTRL_L, CTRL_R) after expansion
        - M is the set of ALT variants (ALT_L, ALT_R) after expansion
        - D is the set of CMD variants (CMD_L, CMD_R) after expansion
        - S is the set of SHIFT variants (SHIFT_L, SHIFT_R) after expansion

        Args:
            modifiers (set[ModifierKey]): The set of modifier keys to
            normalize.

        Returns:
            list[set[ModifierKey]]: A list of sets, each containing a unique
            combination of modifier keys.
        """

        specific_mods = {mod for mod in modifiers if not mod.is_general()}

        variant_combinations = []
        for mod in modifiers:
            if mod.is_general():
                variant_combinations.append([mod.left(), mod.right()])

        expanded_combinations = tuple(itertools.product(*variant_combinations))

        mods = []
        for comb in expanded_combinations:
            mods.append(set(comb) | specific_mods)

        return mods

    def _normalize_key(self, key: str | Key | None) -> str | Key | None:
        """
        Normalize a key by converting shifted characters to their
        non-shifted equivalents. If the key is a Key object or None,
        or not a shifted character, it is returned unchanged.

        Args:
            key (str | Key | None): The key to normalize.

        Returns:
            str | Key | None: The normalized key.
        """

        if isinstance(key, str):
            return normalize_char(key)
        return key

    def _init_callbacks(
        self,
        callbacks: dict[KeySequence, Callable[[], None]] | None = None,
    ):
        """
        Initialize the callback mapping for key sequences.

        Args:
            callbacks (dict[KeySequence, Callable[[], None]] | None): Optional
            callback mapping for key sequences. Default is None.
        """

        if not callbacks:
            callbacks = {}

        self._callbacks_exact = {}
        self._callbacks_subset = []

        # Create a mapping for all possible modifier variant subsets for fast
        # loopup during key events (for exact modifier matches)
        for subset in self._generate_modifier_subsets():
            key = KeySequence(None, frozenset(subset))
            self._callbacks_exact[key] = {}

        for k, cb in callbacks.items():
            # Create a copy of the key sequence to avoid users affecting
            # internal state by modifying the original object after
            # registration
            k_copy = KeySequence(
                key=k.key,
                modifiers=k.modifiers,
                repeat=k.repeat,
                ignore_modifiers=k.ignore_modifiers,
            )

            normalized_modifiers = self._normalize_modifiers(k.modifiers)

            for mod_comb in normalized_modifiers:
                mod_set = KeySequence(None, frozenset(mod_comb))

                if k.ignore_modifiers:
                    # We store subset matching callbacks in a separate list
                    self._callbacks_subset.append((k_copy, cb))
                else:
                    self._callbacks_exact[mod_set][k_copy] = cb

    def _trigger(self, k: KeySequence, cb: Callable[[], None]):
        """
        Trigger the callback for the given key sequence.

        Args:
            k (KeySequence): The key sequence to trigger.
            cb (Callable[[], None]): The callback function to execute.
        """

        # Call the callback if the key sequence is a repeat action
        if k.repeat:
            self._thread_pool.submit(cb)
        # If not a repeat action, only call if the key is not already pressed
        elif not k.repeat and k not in self._keys_pressed:
            self._keys_pressed.add(k)
            self._thread_pool.submit(cb)

    def _on_press(self, key):
        """
        Callback function for key press event.
        """

        if not self._callbacks_exact:
            return

        modifier = ModifierKey.from_pynput(key)
        if modifier:
            # If both sides of the modifier were already pressed but we receive
            # another press event for one side, we treat it as a release for
            # that side.
            # This is a workaround for a pynput bug where pressing both sides
            # of a modifier key and releasing one side generates a press event
            # instead of a release event.
            if modifier in self._modifiers and modifier.opposite() in self._modifiers:
                self._on_release(key)
                return
            self._modifiers.add(modifier)

        if hasattr(key, "char") and key.char:
            seq_key = normalize_char(key.char)
        else:
            seq_key = Key.from_pynput(key)

        pressed_mods = frozenset(self._modifiers)
        mod_set = KeySequence(None, pressed_mods)

        # Exact modifier match callbacks
        for k, cb in self._callbacks_exact[mod_set].items():
            if k.key == seq_key:
                self._trigger(k, cb)

        # Subset modifier match callbacks
        for k, cb in self._callbacks_subset:
            if k.key != seq_key:
                continue

            # Check if the key sequence's modifiers are a subset of the
            # pressed modifiers
            if k.modifiers.issubset(pressed_mods):
                self._trigger(k, cb)

    def _on_release(self, key):
        """
        Callback function for key release event.
        """

        if not self._callbacks_exact:
            return

        modifier = ModifierKey.from_pynput(key)
        if modifier:
            for k in list(self._keys_pressed):
                if modifier in k.modifiers:
                    self._keys_pressed.discard(k)
                # Check if the opposite side modifier is pressed.
                # It could be the case that the opposite side is still pressed
                # so we don't want to discard the key in that case.
                if (
                    modifier.opposite() not in self._modifiers
                    and modifier.general() in k.modifiers
                ):
                    self._keys_pressed.discard(k)
            self._modifiers.discard(modifier)

        if hasattr(key, "char") and key.char:
            for k in list(self._keys_pressed):
                if k.key == normalize_char(key.char):
                    self._keys_pressed.discard(k)

    def start(self):
        """
        Start the key listener thread.
        """

        if self._listener:
            self._listener.start()

    def stop(self):
        """
        Stop the key listener.
        """

        if self._listener:
            self._listener.stop()

        if self._owns_thread_pool and self._thread_pool:
            try:
                # We don't wait for tasks to complete to avoid blocking
                self._thread_pool.shutdown(wait=False)
            except Exception as e:
                self._logger.error(f"Error shutting down thread pool: {e}")

    def join(self):
        """
        Wait for the key listener thread to complete.
        """

        if self._listener:
            self._listener.join()
