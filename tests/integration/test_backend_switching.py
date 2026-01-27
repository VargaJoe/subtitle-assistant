"""
Integration tests for backend switching between Ollama and MarianMT.
"""

import pytest
import unittest.mock as mock
from pathlib import Path
import tempfile
import os

from subtitle_translator.config import Config
from subtitle_translator.translator import SubtitleTranslator
from subtitle_translator.core import registry


class TestBackendSwitching:
    """Test suite for backend switching functionality."""
    
    def setup_method(self):
        """Set up test data and configurations."""
        # Sample SRT content
        self.sample_srt_content = """1
00:00:01,000 --> 00:00:03,000
Hello world

2
00:00:04,000 --> 00:00:06,000
How are you?

3
00:00:07,000 --> 00:00:09,000
Good morning
"""
        
        # Create base config
        self.base_config_data = {
            "translation": {
                "source_language": "en",
                "target_language": "hu",
                "model": "test-model",
                "backend": "ollama"
            },
            "ollama": {
                "host": "localhost",
                "port": 11434,
                "timeout": 30
            },
            "processing": {
                "translation_mode": "line-by-line",
                "batch_size": 3,
                "resume_enabled": False
            },
            "multi_model": {
                "enabled": False
            }
        }
    
    def test_config_backend_selection_ollama(self):
        """Test config correctly sets Ollama backend."""
        config_data = self.base_config_data.copy()
        config_data["translation"]["backend"] = "ollama"
        
        config = Config.from_dict(config_data)
        assert config.translation_backend == "ollama"
        assert config.source_lang == "en"
        assert config.target_lang == "hu"
    
    def test_config_backend_selection_marian(self):
        """Test config correctly sets MarianMT backend."""
        config_data = self.base_config_data.copy()
        config_data["translation"]["backend"] = "marian"
        
        config = Config.from_dict(config_data)
        assert config.translation_backend == "marian"
        assert config.source_lang == "en"
        assert config.target_lang == "hu"
    
    def test_config_invalid_backend(self):
        """Test config validation with invalid backend."""
        config_data = self.base_config_data.copy()
        config_data["translation"]["backend"] = "invalid"
        
        with pytest.raises(ValueError, match="Translation backend 'invalid' is not available"):
            Config.from_dict(config_data)
    
    @mock.patch.object(registry, 'get_provider')
    def test_translator_init_ollama_backend(self, mock_get_provider):
        """Test translator initialization with Ollama backend."""
        # Mock the provider
        mock_client = mock.Mock()
        mock_client.is_available.return_value = True
        mock_client.get_available_models.return_value = ["test-model", "another-model"]
        mock_get_provider.return_value = mock_client
        
        config = Config(translation_backend="ollama", model="test-model")
        translator = SubtitleTranslator(config)
        
        assert translator.config.translation_backend == "ollama"
        assert translator.translation_client == mock_client
        assert translator.ollama_client == mock_client  # Backwards compatibility
        
        # Verify get_provider was called
        mock_get_provider.assert_called_once_with("ollama", config.__dict__)
    
    @mock.patch.object(registry, 'get_provider')
    def test_translator_init_marian_backend(self, mock_get_provider):
        """Test translator initialization with MarianMT backend."""
        # Mock the provider
        mock_client = mock.Mock()
        mock_client.is_available.return_value = True
        mock_client.get_available_models.return_value = ["Helsinki-NLP/opus-mt-en-hu"]
        mock_get_provider.return_value = mock_client
        
        config = Config(translation_backend="marian", source_lang="en", target_lang="hu")
        translator = SubtitleTranslator(config)
        
        assert translator.config.translation_backend == "marian"
        assert translator.translation_client == mock_client
        assert translator.ollama_client is None  # Should be None for MarianMT
        
        # Verify get_provider was called
        mock_get_provider.assert_called_once_with("marian", config.__dict__)
    
    def test_translator_init_invalid_backend(self):
        """Test translator initialization with invalid backend."""
        with pytest.raises(ValueError, match="Translation backend 'invalid' is not available"):
            config = Config(translation_backend="invalid")
            SubtitleTranslator(config)
    
    @mock.patch.object(registry, 'get_provider')
    def test_translator_ollama_connection_error(self, mock_get_provider):
        """Test translator initialization when Ollama is not available."""
        # Mock provider to be unavailable
        mock_client = mock.Mock()
        mock_client.is_available.return_value = False
        mock_get_provider.return_value = mock_client
        
        config = Config(translation_backend="ollama")
        
        with pytest.raises(ConnectionError, match="Cannot connect to Ollama"):
            SubtitleTranslator(config)
    
    @mock.patch.object(registry, 'get_provider')
    def test_translator_marian_connection_error(self, mock_get_provider):
        """Test translator initialization when MarianMT is not available."""
        # Mock provider to be unavailable
        mock_client = mock.Mock()
        mock_client.is_available.return_value = False
        mock_get_provider.return_value = mock_client
        
        config = Config(translation_backend="marian")
        
        with pytest.raises(ConnectionError, match="Cannot initialize MARIAN backend"):
            SubtitleTranslator(config)
    
    @mock.patch.object(registry, 'get_provider')
    def test_marian_backend_disables_multimodel(self, mock_get_provider):
        """Test that multi-model is disabled when using MarianMT backend."""
        # Mock the provider
        mock_client = mock.Mock()
        mock_client.is_available.return_value = True
        mock_client.get_available_models.return_value = ["Helsinki-NLP/opus-mt-en-hu"]
        mock_get_provider.return_value = mock_client
        
        # Enable multi-model in config
        config = Config(
            translation_backend="marian",
            source_lang="en",
            target_lang="hu"
        )
        config.multi_model.enabled = True  # Enable multi-model
        
        translator = SubtitleTranslator(config)
        
        # Multi-model should be disabled
        assert translator.config.multi_model.enabled is False
    
    @mock.patch.object(registry, 'get_provider')
    def test_translation_client_method_calls(self, mock_get_provider):
        """Test that translation methods are called on the correct client."""
        # Mock the provider calls - we'll return different mocks for different backends
        call_count = 0
        def mock_provider_factory(backend, config_dict):
            nonlocal call_count
            call_count += 1
            if backend == "ollama":
                mock_client = mock.Mock()
                mock_client.is_available.return_value = True
                mock_client.get_available_models.return_value = ["test-model"]
                mock_client.translate_with_retry.return_value = "Translated text"
                return mock_client
            elif backend == "marian":
                mock_client = mock.Mock()
                mock_client.is_available.return_value = True
                mock_client.get_available_models.return_value = ["Helsinki-NLP/opus-mt-en-hu"]
                mock_client.translate_with_retry.return_value = "Lefordított szöveg"
                return mock_client
        
        mock_get_provider.side_effect = mock_provider_factory
        
        # Test with Ollama backend
        ollama_config = Config(translation_backend="ollama", model="test-model")
        ollama_translator = SubtitleTranslator(ollama_config)
        
        # Test with MarianMT backend
        marian_config = Config(translation_backend="marian", source_lang="en", target_lang="hu")
        marian_translator = SubtitleTranslator(marian_config)
        
        # Verify correct clients are used (they should be different mock objects)
        assert ollama_translator.translation_client is not None
        assert marian_translator.translation_client is not None
        assert ollama_translator.translation_client != marian_translator.translation_client
    
    @mock.patch.object(registry, 'get_provider')
    def test_validate_setup_ollama(self, mock_get_provider):
        """Test validate_setup method with Ollama backend."""
        mock_client = mock.Mock()
        mock_client.is_available.return_value = True
        mock_client.get_available_models.return_value = ["test-model"]
        mock_get_provider.return_value = mock_client
        
        config = Config(translation_backend="ollama", model="test-model")
        translator = SubtitleTranslator(config)
        
        assert translator.validate_setup() is True
    
    @mock.patch.object(registry, 'get_provider')
    def test_validate_setup_marian(self, mock_get_provider):
        """Test validate_setup method with MarianMT backend."""
        mock_client = mock.Mock()
        mock_client.is_available.return_value = True
        mock_client.get_available_models.return_value = ["Helsinki-NLP/opus-mt-en-hu"]
        mock_get_provider.return_value = mock_client
        
        config = Config(translation_backend="marian", source_lang="en", target_lang="hu")
        translator = SubtitleTranslator(config)
        
        assert translator.validate_setup() is True


class TestConfigYAMLBackendSupport:
    """Test YAML configuration file support for backend selection."""
    
    def test_yaml_config_with_backend(self):
        """Test loading YAML config with backend selection."""
        yaml_content = """
translation:
  backend: "marian"
  source_language: "en"
  target_language: "hu"
  model: "test-model"

ollama:
  host: "localhost"
  port: 11434
  timeout: 30

processing:
  translation_mode: "line-by-line"
  batch_size: 3

multi_model:
  enabled: false
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            
            try:
                config = Config.from_yaml(Path(f.name))
                assert config.translation_backend == "marian"
                assert config.source_lang == "en"
                assert config.target_lang == "hu"
            finally:
                try:
                    os.unlink(f.name)
                except PermissionError:
                    pass  # Windows file permission issue, ignore    def test_yaml_config_default_backend(self):
        """Test YAML config uses default backend when not specified."""
        yaml_content = """
translation:
  source_language: "en"
  target_language: "hu"
  model: "test-model"

ollama:
  host: "localhost"
  port: 11434
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            
            try:
                config = Config.from_yaml(Path(f.name))
                assert config.translation_backend == "ollama"  # Default backend
            finally:
                try:
                    os.unlink(f.name)
                except PermissionError:
                    pass  # Windows file permission issue, ignore
if __name__ == "__main__":
    pytest.main([__file__])
