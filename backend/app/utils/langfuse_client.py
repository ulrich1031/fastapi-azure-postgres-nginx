from typing import Optional, Dict
from langfuse import Langfuse
from langfuse.callback import CallbackHandler
from langfuse.client import StatefulSpanClient, StatefulTraceClient, StatefulClient
from langchain_core.output_parsers import JsonOutputParser
from langchain.prompts import PromptTemplate
from app.exceptions.langfuse_exceptions import *
from app.config import get_settings
from app.utils.logging import AppLogger

logger = AppLogger().get_logger()


class LangFuseCallback:
    callback = None

    def __init__(self, cfg=None):
        """
        Initializes the langfuse callback with the given credentials.
        """
        if cfg is None:
            cfg = {}
        self.settings = get_settings()
        default_cfg = {
            "secret_key": self.settings.LANGFUSE_SECRET_KEY,
            "public_key": self.settings.LANGFUSE_PUBLIC_KEY,
            "host": self.settings.LANGFUSE_HOST,
        }
        final_cfg = {**default_cfg, **cfg}
        
        self.callback = CallbackHandler(**final_cfg)


class LangFuseClient:
    """
    A client to interact with the LangFuse service.

    Attributes:
        client (Langfuse): An instance of the Langfuse

    Example:
        >>> client = LangFuseClient()
        >>> # Using custom configuration
        >>> custom_cfg = {
        >>>     "secret_key": "my_secret_key",
        >>>     "public_key": "my_public_key",
        >>>     "host": "https://lanfuse.getara.ai"
        >>> }
        >>> client = LangFuseClient(cfg=custom_cfg)
    """

    client = None

    def __init__(self, cfg=None):
        """
        Initializes the langfuse client instance with the given credentials.

        Parameters:

             cfg (dict, optional): A dictionary containing optional configuration settings.
                                  Expected keys in the dictionary include 'secret_key',
                                  'public_key', and 'host'. These settings will override the
                                  default values obtained from the settings module if provided.
                                  If 'cfg' is not specified or is None, the client will use
                                  the default configuration from the environment variables.
        """
        if cfg is None:
            cfg = {}
        self.settings = get_settings()
        default_cfg = {
            "secret_key": self.settings.LANGFUSE_SECRET_KEY,
            "public_key": self.settings.LANGFUSE_PUBLIC_KEY,
            "host": self.settings.LANGFUSE_HOST,
        }
        final_cfg = {**default_cfg, **cfg}
        # print(final_cfg)
        self.client = Langfuse(**final_cfg)
    
    def get_trace_from_args(self, args: Optional[Dict]):
        """
        Get trace object from the given args.
        If args contains "id", this function will fetch trace by that id and ignore other fields.
        Otherwise, this function will create trace with the given args.
        
        Parameters:

            args (Optional[Dict]): config arguments for the trace.
        """
        if args == None:
            return None
        
        if "id" in args:
            langfuse_trace = self.client.fetch_trace(
                args["id"]
            )
        else:
            langfuse_trace = self.client.trace(
                **args
            )
        return langfuse_trace

    def get_prompt(self, **kwargs):
        if "label" not in kwargs:
            kwargs["label"] = "latest"

        try:
            prompt = self.client.get_prompt(**kwargs)
            return prompt
        except:
            raise PromptNotExit

    def get_prompt_str(self, **kwargs) -> str:
        """
        Fetch langfuse prompt as str
        """
        prompt = self.get_prompt(**kwargs)
        return prompt.prompt

    def get_langchain_prompt_template(self, parser: JsonOutputParser, **kwargs):
        """
        Fetch prompt from langfuse and return it as langchain PromptTemplate.
        """

        prompt = self.get_prompt(**kwargs)
        return PromptTemplate(
            template=prompt.prompt,
            input_variables=prompt.config["input_variables"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )