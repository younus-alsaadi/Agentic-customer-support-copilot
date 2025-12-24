from dataclasses import dataclass
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.helpers.config import get_settings
from src.llms.ProviderFactory_LLM import LLMProviderFactory

from src.llms.templates.template_parser import TemplateParser


@dataclass
class DependencyContainer:
    settings: any
    db_engine: AsyncEngine
    db_client: sessionmaker
    generation_client: any
    embedding_client: any
    template_parser: TemplateParser

    @classmethod
    async def create(cls) -> "DependencyContainer":
        """
        Build all shared dependencies once.
        Use this in FastAPI startup and in eval scripts.
        """
        settings = get_settings()

        # DB
        postgres_conn = (
            f"postgresql+asyncpg://{settings.POSTGRES_USERNAME}:"
            f"{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:"
            f"{settings.POSTGRES_PORT}/{settings.POSTGRES_MAIN_DATABASE}"
        )
        db_engine = create_async_engine(postgres_conn)

        db_client = sessionmaker(
            db_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        # LLM factories
        llm_provider_factory = LLMProviderFactory(settings)


        # generation client
        generation_client = llm_provider_factory.create(
            provider=settings.GENERATION_BACKEND
        )
        generation_client.set_generation_model(model_id=settings.GENERATION_MODEL_ID)

        # embedding client
        embedding_client = llm_provider_factory.create(
            provider=settings.EMBEDDING_BACKEND
        )
        embedding_client.set_embedding_model(
            model_id=settings.EMBEDDING_MODEL_ID,
            embedding_dimensions_size=settings.EMBEDDING_MODEL_SIZE,
        )



        # templates
        template_parser = TemplateParser(
            language=settings.PRIMARY_LANG,
            default_language=settings.DEFAULT_LANG,
        )

        return cls(
            settings=settings,
            db_engine=db_engine,
            db_client=db_client,
            generation_client=generation_client,
            embedding_client=embedding_client,
            template_parser=template_parser,
        )

    async def shutdown(self):
        """Clean shutdown for FastAPI and scripts."""
        await self.vectordb_client.disconnect()
        await self.db_engine.dispose()
