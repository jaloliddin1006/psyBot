"""
ChromaDB Manager for OpenAI RAG functionality
"""
import logging
import uuid
from typing import List, Dict, Optional
import chromadb
import os

logger = logging.getLogger(__name__)


class ChromaManager:
    """ChromaDB ni boshqarish uchun class"""
    
    def __init__(self, collection_name: str = "pdf_documents", embedding_model: str = "openai"):
        """ChromaDB Manager yaratish"""
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.client = None
        self.collection = None
        self.initialize()
    
    def initialize(self):
        """ChromaDB ni ishga tushirish"""
        try:
            # ChromaDB client yaratish (persistent)
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            chroma_path = os.path.join(base_dir, "chroma_db")
            self.client = chromadb.PersistentClient(path=chroma_path)
            
            # Collection yaratish yoki olish
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            
            logger.info(f"ChromaDB collection '{self.collection_name}' tayyor")
            
        except Exception as e:
            logger.error(f"ChromaDB ishga tushirishda xatolik: {e}")
            raise
    
    def add_document(self, doc_id: str, text: str, embedding: List[float], metadata: Dict):
        """ChromaDB ga hujjat qo'shish"""
        try:
            self.collection.add(
                ids=[doc_id],
                documents=[text],
                embeddings=[embedding],
                metadatas=[metadata]
            )
            logger.debug(f"Hujjat qo'shildi: {doc_id}")
            
        except Exception as e:
            logger.error(f"Hujjat qo'shishda xatolik ({doc_id}): {e}")
            raise
    
    def add_documents(self, texts: List[str], embeddings: List[List[float]], metadatas: List[Dict]):
        """Bir nechta hujjatni qo'shish"""
        try:
            if not texts or not embeddings or not metadatas:
                logger.warning("Bo'sh ma'lumot berildi")
                return
            
            if len(texts) != len(embeddings) or len(texts) != len(metadatas):
                raise ValueError("texts, embeddings va metadatas uzunligi bir xil bo'lishi kerak")
            
            # ID larni yaratish
            ids = [str(uuid.uuid4()) for _ in texts]
            
            self.collection.add(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas
            )
            
            logger.info(f"{len(texts)} ta hujjat qo'shildi")
            
        except Exception as e:
            logger.error(f"Hujjatlar qo'shishda xatolik: {e}")
            raise
    
    def search(self, query_embedding: List[float], n_results: int = 5) -> Dict:
        """Vector search qilish"""
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            return results
            
        except Exception as e:
            logger.error(f"Search xatolik: {e}")
            return {"documents": [], "metadatas": [], "distances": []}
    
    def hybrid_search(self, query_text: str, query_embedding: List[float], n_results: int = 4) -> Dict:
        """Hybrid search - text va vector search ni birlashtirish"""
        try:
            # Vector search
            vector_results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            
            # Text search ham qo'shamiz (where clause orqali)
            try:
                text_results = self.collection.query(
                    query_texts=[query_text],
                    n_results=n_results -1
                )
                
                # Natijalarni birlashtirish (sodda usul)
                combined_docs = vector_results['documents'][0] if vector_results['documents'] else []
                combined_metadata = vector_results['metadatas'][0] if vector_results['metadatas'] else []
                
                # Text search natijalarini qo'shish (duplikatsiz)
                if text_results and text_results['documents']:
                    for i, doc in enumerate(text_results['documents'][0]):
                        if doc not in combined_docs:
                            combined_docs.append(doc)
                            if text_results['metadatas'] and text_results['metadatas'][0]:
                                combined_metadata.append(text_results['metadatas'][0][i])
                
                return {
                    'documents': [combined_docs[:n_results]],
                    'metadatas': [combined_metadata[:n_results]]
                }
                
            except:
                # Agar text search ishlamasa, faqat vector search natijasini qaytarish
                return vector_results
            
        except Exception as e:
            logger.error(f"Hybrid search xatolik: {e}")
            return {"documents": [], "metadatas": []}
    
    def get_count(self) -> int:
        """Collection dagi hujjatlar sonini olish"""
        try:
            return self.collection.count()
        except Exception as e:
            logger.error(f"Count olishda xatolik: {e}")
            return 0
    
    def clear_collection(self) -> bool:
        """Collection ni tozalash"""
        try:
            # Collection ni o'chirish
            self.client.delete_collection(name=self.collection_name)
            
            # Qayta yaratish
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            
            logger.info(f"Collection '{self.collection_name}' tozalandi")
            return True
            
        except Exception as e:
            logger.error(f"Collection tozalashda xatolik: {e}")
            return False
    
    def delete_document(self, doc_id: str) -> bool:
        """Bitta hujjatni o'chirish"""
        try:
            self.collection.delete(ids=[doc_id])
            logger.info(f"Hujjat o'chirildi: {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Hujjat o'chirishda xatolik ({doc_id}): {e}")
            return False
    
    def get_all_documents(self) -> Dict:
        """Barcha hujjatlarni olish"""
        try:
            return self.collection.get()
        except Exception as e:
            logger.error(f"Hujjatlar olishda xatolik: {e}")
            return {"documents": [], "metadatas": [], "ids": []}