import re
from typing import Dict

class StringUtil:
    
    @classmethod
    def cleanse_text(self, text):
        return text.replace('\x00', '') if text else text  
    
    @classmethod
    def extract_urls(self, text):  
        url_pattern = re.compile(  
            r'(https?://(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|www\.[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|https?://(?:www\.|(?!www))[a-zA-Z0-9]+\.[^\s]{2,}|www\.[a-zA-Z0-9]+\.[^\s]{2,})')  
        urls = re.findall(url_pattern, text)  
        return urls  
    
    @classmethod
    def extract_chunks_and_content(self, content: str) -> Dict:
        """
        Extract pure content and citation from content.
        
        Example Input:
        
            "The workshops were held weekly, featuring a diverse range of art activities designed to enhance creativity and fine motor skills.<citation></citation>"
        
        Example Output:
        
            {
                'content': 'The workshops were held weekly, featuring a diverse range of art activities designed to enhance creativity and fine motor skills.',
                'citations': [
                    '100c744f-ded7-44df-b4fe-e682a11afb5c'
                ]
            }
        """
        citation_pattern = re.compile(r"<citation>(.*?)</citation>")
    
        # Find all citations and ensure uniqueness using a set
        citations_set = set(citation_pattern.findall(content))
        
        # Remove all citation tags from content
        raw_content = citation_pattern.sub('', content).strip()
        
        return {
            'content': raw_content,
            'citations': list(citations_set)
        }