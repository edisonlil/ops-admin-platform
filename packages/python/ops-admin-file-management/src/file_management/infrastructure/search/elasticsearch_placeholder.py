from __future__ import annotations


class NoopFileIndexer:
    def index_file(self, file_id: int) -> None:
        _ = file_id

    def remove_file(self, file_id: int) -> None:
        _ = file_id
