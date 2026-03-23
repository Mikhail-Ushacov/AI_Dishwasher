from typing import Dict, Type, Callable, Any


class Registry:
    _environments: Dict[str, Callable] = {}
    _agents: Dict[str, Callable] = {}
    _models: Dict[str, Type] = {}
    _observations: Dict[str, Type] = {}
    _trainers: Dict[str, Type] = {}
    
    @classmethod
    def register_env(cls, name: str):
        def decorator(func: Callable):
            cls._environments[name] = func
            return func
        return decorator
    
    @classmethod
    def register_agent(cls, name: str):
        def decorator(func: Callable):
            cls._agents[name] = func
            return func
        return decorator
    
    @classmethod
    def register_model(cls, name: str):
        def decorator(cls_model: Type):
            cls._models[name] = cls_model
            return cls_model
        return decorator
    
    @classmethod
    def register_observation(cls, name: str):
        def decorator(cls_obs: Type):
            cls._observations[name] = cls_obs
            return cls_obs
        return decorator
    
    @classmethod
    def register_trainer(cls, name: str):
        def decorator(cls_trainer: Type):
            cls._trainers[name] = cls_trainer
            return cls_trainer
        return decorator
    
    @classmethod
    def get_env(cls, name: str, **kwargs):
        if name not in cls._environments:
            available = list(cls._environments.keys())
            raise ValueError(f"Unknown env: {name}. Available: {available}")
        return cls._environments[name](**kwargs)
    
    @classmethod
    def get_agent(cls, name: str, **kwargs):
        if name not in cls._agents:
            available = list(cls._agents.keys())
            raise ValueError(f"Unknown agent: {name}. Available: {available}")
        return cls._agents[name](**kwargs)
    
    @classmethod
    def get_model(cls, name: str, **kwargs):
        if name not in cls._models:
            available = list(cls._models.keys())
            raise ValueError(f"Unknown model: {name}. Available: {available}")
        return cls._models[name](**kwargs)
    
    @classmethod
    def get_observation(cls, name: str, **kwargs):
        if name not in cls._observations:
            available = list(cls._observations.keys())
            raise ValueError(f"Unknown observation: {name}. Available: {available}")
        return cls._observations[name](**kwargs)
    
    @classmethod
    def list_available(cls) -> Dict[str, list]:
        return {
            'environments': list(cls._environments.keys()),
            'agents': list(cls._agents.keys()),
            'models': list(cls._models.keys()),
            'observations': list(cls._observations.keys()),
            'trainers': list(cls._trainers.keys())
        }
