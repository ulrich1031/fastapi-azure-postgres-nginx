
class PromptNotExit(Exception):
    def __init__(self, name=""):
        self.message = f"""
        Prompt {name} not exist
        """
