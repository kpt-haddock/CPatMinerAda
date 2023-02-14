class ChangedFile:
    new_path: str
    new_content: str
    old_path: str
    old_content: str

    def __init__(self, new_path: str, new_content: str, old_path: str, old_content: str):
        self.new_path = new_path
        self.new_content = new_content
        self.old_path = old_path
        self.old_content = old_content
