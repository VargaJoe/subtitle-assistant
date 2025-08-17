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
        
        with pytest.raises(ValueError, match="Translation backend must be 'ollama' or 'marian'"):
            Config.from_dict(config_data)
    
    @mock.patch('subtitle_translator.translator.OllamaClient')
    def test_translator_init_ollama_backend(self, mock_ollama_client_class):
        """Test translator initialization with Ollama backend."""
        # Mock OllamaClient
        mock_client = mock.Mock()
        mock_client.is_available.return_value = True
        mock_client.get_available_models.return_value = ["test-model", "another-model"]
        mock_ollama_client_class.return_value = mock_client
        
        config = Config(translation_backend="ollama", model="test-model")
        translator = SubtitleTranslator(config)
        
        assert translator.config.translation_backend == "ollama"
        assert translator.translation_client == mock_client
        assert translator.ollama_client == mock_client  # Backwards compatibility
        
        # Verify OllamaClient was initialized
        mock_ollama_client_class.assert_called_once_with(config)
    
    @mock.patch('subtitle_translator.translator.MarianClient')
    def test_translator_init_marian_backend(self, mock_marian_client_class):
        """Test translator initialization with MarianMT backend."""
        # Mock MarianClient
        mock_client = mock.Mock()
        mock_client.is_available.return_value = True
        mock_client.get_available_models.return_value = ["NYTK/translation-marianmt-en-hu"]
        mock_marian_client_class.return_value = mock_client
        
        config = Config(translation_backend="marian", source_lang="en", target_lang="hu")
        translator = SubtitleTranslator(config)
        
        assert translator.config.translation_backend == "marian"
        assert translator.translation_client == mock_client
        assert translator.ollama_client is None  # Should be None for MarianMT
        
        # Verify MarianClient was initialized
        mock_marian_client_class.assert_called_once_with(config)
    
    def test_translator_init_invalid_backend(self):
        """Test translator initialization with invalid backend."""
        config = Config(translation_backend="invalid")
        
        with pytest.raises(ValueError, match="Unsupported translation backend: invalid"):
            SubtitleTranslator(config)
    
    @mock.patch('subtitle_translator.translator.OllamaClient')
    def test_translator_ollama_connection_error(self, mock_ollama_client_class):
        """Test translator initialization when Ollama is not available."""
        # Mock OllamaClient to be unavailable
        mock_client = mock.Mock()
        mock_client.is_available.return_value = False
        mock_ollama_client_class.return_value = mock_client
        
        config = Config(translation_backend="ollama")
        
        with pytest.raises(ConnectionError, match="Cannot connect to Ollama"):
            SubtitleTranslator(config)
    
    @mock.patch('subtitle_translator.translator.MarianClient')
    def test_translator_marian_connection_error(self, mock_marian_client_class):
        """Test translator initialization when MarianMT is not available."""
        # Mock MarianClient to be unavailable
        mock_client = mock.Mock()
        mock_client.is_available.return_value = False
        mock_marian_client_class.return_value = mock_client
        
        config = Config(translation_backend="marian")
        
        with pytest.raises(ConnectionError, match="Cannot initialize MARIAN backend"):
            SubtitleTranslator(config)
    
    @mock.patch('subtitle_translator.translator.MarianClient')
    def test_marian_backend_disables_multimodel(self, mock_marian_client_class):
        """Test that multi-model is disabled when using MarianMT backend."""
        # Mock MarianClient
        mock_client = mock.Mock()
        mock_client.is_available.return_value = True
        mock_client.get_available_models.return_value = ["NYTK/translation-marianmt-en-hu"]
        mock_marian_client_class.return_value = mock_client
        
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
    
    @mock.patch('subtitle_translator.translator.OllamaClient')
    @mock.patch('subtitle_translator.translator.MarianClient')
    def test_translation_client_method_calls(self, mock_marian_class, mock_ollama_class):
        """Test that translation methods are called on the correct client."""
        # Mock both clients
        mock_ollama_client = mock.Mock()
        mock_ollama_client.is_available.return_value = True
        mock_ollama_client.get_available_models.return_value = ["test-model"]
        mock_ollama_client.translate_with_retry.return_value = "Translated text"
        mock_ollama_class.return_value = mock_ollama_client
        
        mock_marian_client = mock.Mock()
        mock_marian_client.is_available.return_value = True
        mock_marian_client.get_available_models.return_value = ["NYTK/translation-marianmt-en-hu"]
        mock_marian_client.translate_with_retry.return_value = "Lefordított szöveg"
        mock_marian_class.return_value = mock_marian_client
        
        # Test with Ollama backend
        ollama_config = Config(translation_backend="ollama", model="test-model")
        ollama_translator = SubtitleTranslator(ollama_config)
        
        # Test with MarianMT backend
        marian_config = Config(translation_backend="marian", source_lang="en", target_lang="hu")
        marian_translator = SubtitleTranslator(marian_config)
        
        # Verify correct clients are used
        assert ollama_translator.translation_client == mock_ollama_client
        assert marian_translator.translation_client == mock_marian_client
    
    def test_validate_setup_ollama(self):
        """Test validate_setup method with Ollama backend."""
        with mock.patch('subtitle_translator.translator.OllamaClient') as mock_ollama_class:
            mock_client = mock.Mock()
            mock_client.is_available.return_value = True
            mock_client.get_available_models.return_value = ["test-model"]
            mock_ollama_class.return_value = mock_client
            
            config = Config(translation_backend="ollama", model="test-model")
            translator = SubtitleTranslator(config)
            
            assert translator.validate_setup() is True
    
    def test_validate_setup_marian(self):
        """Test validate_setup method with MarianMT backend."""
        with mock.patch('subtitle_translator.translator.MarianClient') as mock_marian_class:
            mock_client = mock.Mock()
            mock_client.is_available.return_value = True
            mock_client.get_available_models.return_value = ["NYTK/translation-marianmt-en-hu"]
            mock_marian_class.return_value = mock_client
            
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
