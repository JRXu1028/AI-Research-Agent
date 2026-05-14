"""
向量数据库模块
使用 Chroma 管理文档向量
"""

from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from .embeddings import create_embeddings
from .knowledge_base import get_knowledge_base
import os


class VectorStore:
    """向量数据库管理类"""
    
    def __init__(self, persist_directory="./data/chroma_db"):
        """
        初始化向量数据库
        
        Args:
            persist_directory: 数据库持久化目录
        """
        self.persist_directory = persist_directory
        self.embeddings = create_embeddings()
        self.vectorstore = None
        
    def initialize(self, force_reload=False):
        """
        初始化或加载向量数据库
        
        Args:
            force_reload: 是否强制重新加载数据
        """
        # 检查是否已存在数据库
        if os.path.exists(self.persist_directory) and not force_reload:
            print("      加载已有向量数据库...")
            self.vectorstore = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings
            )
            print(f"      已加载 {self.vectorstore._collection.count()} 条文档")
        else:
            print("      创建新的向量数据库...")
            # 加载知识库数据
            knowledge_base = get_knowledge_base()
            
            # 转换为 LangChain Document 格式
            documents = [
                Document(
                    page_content=doc["content"],
                    metadata=doc["metadata"]
                )
                for doc in knowledge_base
            ]
            
            # 创建向量数据库
            self.vectorstore = Chroma.from_documents(
                documents=documents,
                embedding=self.embeddings,
                persist_directory=self.persist_directory
            )
            
            print(f"      已创建向量数据库，包含 {len(documents)} 条文档")
    
    def search(self, query: str, k: int = 3):
        """
        检索相关文档
        
        Args:
            query: 查询文本
            k: 返回的文档数量
        
        Returns:
            相关文档列表
        """
        if not self.vectorstore:
            raise ValueError("向量数据库未初始化，请先调用 initialize()")
        
        # 相似度搜索
        results = self.vectorstore.similarity_search(query, k=k)
        return results
    
    def search_with_score(self, query: str, k: int = 3):
        """
        检索相关文档（带相似度分数）
        
        Args:
            query: 查询文本
            k: 返回的文档数量
        
        Returns:
            (文档, 分数) 的列表
        """
        if not self.vectorstore:
            raise ValueError("向量数据库未初始化，请先调用 initialize()")
        
        # 相似度搜索（带分数）
        results = self.vectorstore.similarity_search_with_score(query, k=k)
        return results
    
    def add_documents(self, documents):
        """
        添加新文档到向量数据库
        
        Args:
            documents: Document 对象列表
        """
        if not self.vectorstore:
            raise ValueError("向量数据库未初始化，请先调用 initialize()")
        
        self.vectorstore.add_documents(documents)
        print(f"      已添加 {len(documents)} 条新文档")


def create_vector_store(force_reload=False):
    """
    创建并初始化向量数据库
    
    Args:
        force_reload: 是否强制重新加载数据
    
    Returns:
        VectorStore 实例
    """
    store = VectorStore()
    store.initialize(force_reload=force_reload)
    return store
