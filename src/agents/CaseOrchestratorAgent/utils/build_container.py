from src.utils.client_deps_container import DependencyContainer

_container = None
async def get_container() -> DependencyContainer:
    global _container
    if _container is None:
        _container = await DependencyContainer.create()
    return _container