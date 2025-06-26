import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

def get_config() -> Dict[str, Any]:
    """Load configuration from environment variables"""
    return {
        'vertex_ai': {
            'project_id': os.getenv('GOOGLE_CLOUD_PROJECT_ID'),
            'location': os.getenv('VERTEX_AI_LOCATION', 'global'),
            'model_name': os.getenv('VERTEX_AI_MODEL_NAME', 'gemini-2.5-flash'),
        },
        'datastore': {
            'website_id': os.getenv('VERTEX_DATASTORE_ID_WEBSITE'),
            'faq_id': os.getenv('VERTEX_DATASTORE_ID_FAQ'),
            'location': os.getenv('VERTEX_DATASTORE_LOCATION', 'us'),
        },
        'app_engine': {
            'website_engine_id': os.getenv('VERTEX_APP_ENGINE_ID_WEBSITE'),
            'faq_engine_id': os.getenv('VERTEX_APP_ENGINE_ID_FAQ'),
            'location': os.getenv('VERTEX_APP_ENGINE_LOCATION', 'us'),
        },
        'agent': {
            'max_retries': int(os.getenv('AGENT_MAX_RETRIES', '3')),
            'timeout': int(os.getenv('AGENT_TIMEOUT_SECONDS', '30')),
            'temperature': float(os.getenv('AGENT_TEMPERATURE', '0.7')),
        },
        'processing': {
            'preprocessing_enabled': os.getenv('PREPROCESSING_ENABLED', 'true').lower() == 'true',
            'postprocessing_enabled': os.getenv('POSTPROCESSING_ENABLED', 'true').lower() == 'true',
            'checker_enabled': os.getenv('CHECKER_ENABLED', 'true').lower() == 'true',
            'url_allowlist': [url.strip() for url in os.getenv('URL_ALLOWLIST', 'https://hsbc.com,https://hsbc.com.hk').split(',') if url.strip()],
        },
        'logging': {
            'level': os.getenv('LOG_LEVEL', 'INFO'),
            'format': os.getenv('LOG_FORMAT', 'json'),
            'file_enabled': os.getenv('LOG_FILE_ENABLED', 'false').lower() == 'true',
            'file_path': os.getenv('LOG_FILE_PATH', 'logs/hsbc_agent.log'),
            'file_max_size': int(os.getenv('LOG_FILE_MAX_SIZE', '10485760')),  # 10MB
            'file_backup_count': int(os.getenv('LOG_FILE_BACKUP_COUNT', '5')),
        }
    }

def validate_config() -> None:
    """Validate that required configuration is present"""
    config = get_config()
    
    required_fields = [
        ('vertex_ai.project_id', config['vertex_ai']['project_id']),
        ('datastore.website_id', config['datastore']['website_id']),
        ('datastore.faq_id', config['datastore']['faq_id']),
        ('app_engine.website_engine_id', config['app_engine']['website_engine_id']),
        ('app_engine.faq_engine_id', config['app_engine']['faq_engine_id']),
    ]
    
    missing_fields = [field for field, value in required_fields if not value]
    
    if missing_fields:
        raise ValueError(f"Missing required configuration: {', '.join(missing_fields)}")

# Global config instance
CONFIG = get_config()