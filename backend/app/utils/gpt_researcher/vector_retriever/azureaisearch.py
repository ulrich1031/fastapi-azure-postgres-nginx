from langchain_community.retrievers import AzureAISearchRetriever


class AzureAISearchVectorRetriever:
    def __init__(self, **kwargs):
        self.retriever = AzureAISearchRetriever(**kwargs)

    def invoke(self, **kwargs):
        return self.retriever.invoke(**kwargs)

    async def ainvoke(self, **kwargs):
        return await self.retriever.ainvoke(**kwargs)
