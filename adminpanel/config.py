from django.core.cache import cache

from .models import SystemConfig


CONFIG_CACHE_KEY = "adminpanel.system_config"
CONFIG_CACHE_TIMEOUT = 60


def get_system_config():
    config = cache.get(CONFIG_CACHE_KEY)
    if config is None:
        config, _ = SystemConfig.objects.get_or_create(pk=1)
        cache.set(CONFIG_CACHE_KEY, config, CONFIG_CACHE_TIMEOUT)
    return config


def clear_system_config_cache():
    cache.delete(CONFIG_CACHE_KEY)
