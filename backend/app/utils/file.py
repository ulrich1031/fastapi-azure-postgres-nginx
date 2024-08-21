import os
import uuid
from typing import List
from fastapi import UploadFile
from langchain_community.document_loaders import PyPDFLoader, TextLoader, UnstructuredWordDocumentLoader, UnstructuredPowerPointLoader
from .string import StringUtil

class FileUtil:
    """
    Utility functions for processing files
    """
    def __init__(self, path_prefix = "./static/files"):
        self.path_prefix = path_prefix
        
    def __replace_source_to_filename__(self, documents: List) -> List:
        """
        Replace source to filename from full path.
        And cleanse page content.
        """
        for document in documents:
            document.page_content = StringUtil.cleanse_text(document.page_content)
            document.metadata['source'] = os.path.basename(document.metadata['source'])
        
        return documents
    
    async def __load_txt_as_documents__(self, file_path: str):
        loader = TextLoader(file_path=file_path)
        return self.__replace_source_to_filename__(await loader.aload())
    
    async def __load_pdf_as_documents__(self, file_path: str):
        loader = PyPDFLoader(file_path, extract_images=True)
        # loader = PyPDFLoader(file_path)
        return self.__replace_source_to_filename__(await loader.aload())
    
    async def __load_docx_as_documents__(self, file_path: str):
        loader = UnstructuredWordDocumentLoader(file_path)
        return self.__replace_source_to_filename__(await loader.aload())
    
    async def __load_pptx_as_documents__(self, file_path: str):
        loader = UnstructuredPowerPointLoader(file_path)
        return self.__replace_source_to_filename__(await loader.aload())
    
    async def load_file_as_documents(self, file_path: str):
        _, ext = os.path.splitext(file_path)
        if ext == ".txt":
            return await self.__load_txt_as_documents__(file_path=file_path)
        elif ext == ".pdf":
            return await self.__load_pdf_as_documents__(file_path=file_path)
        elif ext == ".docx" or ext == "doc":
            return await self.__load_docx_as_documents__(file_path=file_path)
        elif ext == ".pptx":
            return await self.__load_pptx_as_documents__(file_path=file_path)
        return []
        
    async def save_uploaded_file(self, file: UploadFile, file_path="") -> str:
        # Ensure the file_path exists  
        file_path = self.path_prefix + file_path
        if not os.path.exists(file_path):  
            os.makedirs(file_path)
        
        file_name = file.filename
        with open(file_path + file_name, "wb") as f:
            contents = await file.read()  
            f.write(contents)
        return file_path + file_name