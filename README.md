# Introduction

This is a backend service of the report generation platform.

## Report Generation

It automatically searches internal documents, the web, user-uploaded documents, and user-specified URLs for research, and generates a report based on the research data along with citations.

You can check out my demo video here: https://app.screencast.com/MoAlIaayeseXs

### Workflow

1. The user provides the report's target audience, objective, and other additional information related to the report.
   
2. Based on the user's information, the system initiates research.
   
   There are four types of research executed in parallel:
   - Internal Documents Search
     
   Internal documents are the main database shared across all users in the same organization. The system generates 5 search queries to search through the vector store of documents using Azure AI Search, retrieving the top 10 chunks for each query. In total, 50 chunks are returned from this search.
   
   - Web Search
   - 
   The system automatically searches the web to find relevant data for the report. It generates 5 web search queries, conducting the search with Tavily Search Engine and retrieving the top 10 chunks for each query. In total, 50 chunks are returned from this search.

   - User-Specified URLs
     
   Users can specify URLs they want to research for the report. The system leverages the Exa API to find relevant data from these URLs.
   
   - User-Uploaded Files
     
   Users can upload their custom documents for research. The system leverages FAISS in-memory vector store and semantic search to find the most relevant data from the user-uploaded files.

4. The system ranks all chunks returned from the research (50 * 4 = 200) using a Large Language Model (LLM).
   
5. The top 20 chunks are fetched and passed to the LLM as a reference. Optionally, users can select chunks to use, rather than selecting the top 20 chunks. Additionally, users can conduct research with their own queries for all four types of research.

6. Finally, the LLM generates a report based on the given report details and research data, including citations.

7. Users can edit the reports manually using a Tiptap editor.
All of the numbers in the workflow are configurable from user settings.

## AI Assistant

AI assistant that can do web search, url search, and search uploaded files to provides answer to the user.
It can create charts based on user requirements.

You can check out my demo video here: https://app.screencast.com/k3V1ZZwbBG98v

   The agent has access to four external tools that are used to provide up-to-date answers to users:
   
   - Tavily Search Engine
   The agent can call upon the Tavily search engine to retrieve the latest data that the user is asking for.

   - Azure AI Search
   Internal documents are embedded into the Azure AI Search, and the agent is able to search this vector store to find relevant information.

   - Exa API
   In case the user specifies some URLs to use in the message, the agent uses the Exa API to extract relevant information from the provided URLs.

   - HighChart
   The agent calls the HighChart tool to create visualizations.

# Technologies

1. FastAPI as RESTful API framework
   
2. PostgreSQL as a database

3. Alembic for database migration

4. Azure OpenAI as a large language model

5. Azure AI Search as a vector database

6. Tavily search engine

7. Langfuse for llm tracing and prompt management.

8. Docker & Docker compose

# How to run the server on your local

1. Clone the repository: `git clone https://github.com/ulrich1031/fastapi-azure-postgres-nginx.git`

2. Run `make runBuildLocalDocer` to build docker container.

3. Go to `backend` directory.

4. Copy `env.example`, rename it as `.env.local` and replace values with your own.

5. Run `make runLocal` and server will be up on 8001 port.

    You can test the endpionts on `localhost:8000/docs`.
