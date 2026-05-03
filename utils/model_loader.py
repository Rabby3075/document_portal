import os 
import sys
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from utils.config_loader import load_config
from langchain_groq import ChatGroq
#from langchain_openai import ChatOpenAI
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalCustomException



log = CustomLogger().get_logger(__name__)

class ModelLoader:
    """
    A utility class to load embedding and llm models.
    """
    def __init__(self):
        load_dotenv()
        self._validate_environment_variables()
        self.config = load_config()
        log.info("ModelLoader initialized successfully.", config_keys=list(self.config.keys()))

    def _validate_environment_variables(self):
        """
        Validates the presence of required environment variables.
        """
        required_variables = ["GROQ_API_KEY", "GOOGLE_API_KEY"]
        self.api_keys = {key: os.getenv(key) for key in required_variables}
        missing = [k for k, v in self.api_keys.items() if not v]
        if missing:
            log.error(f"Missing required environment variables: {missing}")
            raise DocumentPortalCustomException(f"Missing required environment variables: {missing}", sys)
        log.info("Environment variables validated", available_keys = [k for k in self.api_keys.keys() if self.api_keys[k]])

    def load_embedding_model(self):
        """Loads the embedding model based on the configuration.
        """
        try:
            log.info("Loading embeding model...")
            model_name = self.config["embedding_model"]["model_name"]
            return GoogleGenerativeAIEmbeddings(model=model_name)
        except Exception as e:
            log.error(f"Failed to load embedding model: {e}")
            raise DocumentPortalCustomException(f"Failed to load embedding model: {e}", sys)

    def load_llm(self):
        """Loads the LLM model based on the configuration.
        """
        llm_block = self.config["llm"]
        provider_key = os.getenv("LLM_Provider", "groq") #default to groq if not set
        if provider_key not in llm_block:
            log.error("LLM provider not found in config", provider_key=provider_key)
            raise ValueError(f"LLM provider '{provider_key}' not found in config")
        
        llm_config = llm_block[provider_key]
        provider = llm_config.get("provider")
        model_name = llm_config.get("model_name")
        temperature = llm_config.get("temperature",0.2)
        max_output_tokens = llm_config.get("max_output_tokens",2048)

        log.info("Loading LLM", provider = provider , model_name=model_name, temperature=temperature, max_output_tokens=max_output_tokens)

        if provider == "groq":
            llm = ChatGroq(
                model = model_name,
                api_key = self.api_keys["GROQ_API_KEY"],
                temperature = temperature,
                
            )
        elif provider == "google":
            llm = ChatGoogleGenerativeAI(
                model=model_name,
                api_key=self.api_keys["GOOGLE_API_KEY"],
                temperature=temperature,
            )
        else:
            log.error("Unsupported LLM provider", provider=provider)
            raise ValueError(f"Unsupported LLM provider: {provider}")
        return llm

if __name__ == "__main__":
    loader = ModelLoader()

    #test embedding model
    embedding_model = loader.load_embedding_model()
    print(f"Embedding model loaded successfully - {embedding_model}")

    print("-" * 50)

    #test llm 
    llm = loader.load_llm()
    print(f"LLM model loaded successfully - {llm}")
    
    print("-" * 50)

    result = llm.invoke("What is the capital of France?")
    print(f"LLM response: {result.content}")


