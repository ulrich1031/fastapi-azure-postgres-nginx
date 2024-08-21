from .azureaisearch import AzureAISearchVectorRetriever


def get_vector_retriever(type: str):
    if type == "azureaisearch":
        return AzureAISearchVectorRetriever
