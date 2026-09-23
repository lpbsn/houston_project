from __future__ import annotations


class MamaNiceDatasetError(Exception):
    def __init__(self, messages: tuple[str, ...] | list[str] | str):
        if isinstance(messages, str):
            self.messages = (messages,)
        else:
            self.messages = tuple(messages)
        super().__init__("; ".join(self.messages))


class MamaNiceSeedTargetUntrackedError(MamaNiceDatasetError):
    def __init__(self, seed_key: str):
        super().__init__([f"seed_target_untracked:{seed_key}"])


class MamaNiceSeedTargetMissingError(MamaNiceDatasetError):
    def __init__(self, seed_key: str):
        super().__init__([f"seed_target_missing:{seed_key}"])


class MamaNiceSeedTargetDivergedError(MamaNiceDatasetError):
    def __init__(self, seed_key: str):
        super().__init__([f"seed_target_diverged:{seed_key}"])
