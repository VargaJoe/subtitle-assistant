"""
Tests for MarianMT translation client.
"""

import pytest
import unittest.mock as mock
from pathlib import Path

# Import the MarianClient and related modules
try:
    from subtitle_translator.marian_client import MarianClient
    from subtitle_translator.config import Config
    MARIAN_AVAILABLE = True
except ImportError:
    MARIAN_AVAILABLE = False


@pytest.mark.skipif(not MARIAN_AVAILABLE, reason="MarianMT dependencies not available")
class TestMarianClient:
    """Test suite for MarianClient."""
    
    def setup_method(self):
        """Set up test configuration."""
        self.config = Config(
            source_lang="en",
            target_lang="hu",
            translation_backend="marian",
            verbose=True,
            max_retries=2
        )
    
    @mock.patch('subtitle_translator.marian_client.MarianMTModel')
    @mock.patch('subtitle_translator.marian_client.MarianTokenizer')
    @mock.patch('subtitle_translator.marian_client.torch')
    def test_init_with_mocked_dependencies(self, mock_torch, mock_tokenizer_class, mock_model_class):
        """Test MarianClient initialization with mocked dependencies."""
        # Mock torch.cuda.is_available to return False (CPU mode)
        mock_torch.cuda.is_available.return_value = False
        
        # Mock tokenizer and model
        mock_tokenizer = mock.Mock()
        mock_model = mock.Mock()
        mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer
        mock_model_class.from_pretrained.return_value = mock_model
        
        # Mock model.to() method
        mock_model.to.return_value = mock_model
        
        client = MarianClient(self.config)
        
        assert client.device == "cpu"
        assert client.model == mock_model
        assert client.tokenizer == mock_tokenizer
        
        # Verify model loading was called
        mock_tokenizer_class.from_pretrained.assert_called_once_with(
            "NYTK/translation-marianmt-en-hu",
            cache_dir=client._get_cache_dir()
        )
        mock_model_class.from_pretrained.assert_called_once_with(
            "NYTK/translation-marianmt-en-hu",
            cache_dir=client._get_cache_dir()
        )
    
    def test_get_model_name_en_hu(self):
        """Test model name selection for EN->HU translation."""
        client = MarianClient.__new__(MarianClient)  # Create without calling __init__
        client.config = self.config
        
        model_name = client._get_model_name()
        assert model_name == "NYTK/translation-marianmt-en-hu"
    
    def test_get_model_name_unsupported_pair(self):
        """Test model name selection for unsupported language pair."""
        config = Config(
            source_lang="en",
            target_lang="zh",  # Unsupported language
            translation_backend="marian"
        )
        
        with pytest.raises(ValueError, match="Language pair en->zh is not supported"):
            client = MarianClient.__new__(MarianClient)
            client.config = config
            client._get_model_name()
    
    def test_get_cache_dir(self):
        """Test cache directory creation."""
        client = MarianClient.__new__(MarianClient)  # Create without calling __init__
        cache_dir = client._get_cache_dir()
        
        expected_path = Path.home() / ".cache" / "subtitle-translator" / "marianmt"
        assert cache_dir == expected_path
    
    @mock.patch('subtitle_translator.marian_client.MarianMTModel')
    @mock.patch('subtitle_translator.marian_client.MarianTokenizer')
    @mock.patch('subtitle_translator.marian_client.torch')
    def test_translate_text_basic(self, mock_torch, mock_tokenizer_class, mock_model_class):
        """Test basic text translation."""
        # Setup mocks
        mock_torch.cuda.is_available.return_value = False
        mock_torch.no_grad.return_value.__enter__ = mock.Mock()
        mock_torch.no_grad.return_value.__exit__ = mock.Mock()
        
        mock_tokenizer = mock.Mock()
        mock_model = mock.Mock()
        mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer
        mock_model_class.from_pretrained.return_value = mock_model
        mock_model.to.return_value = mock_model
        
        # Mock tokenizer behavior
        mock_inputs = {"input_ids": mock.Mock(), "attention_mask": mock.Mock()}
        mock_tokenizer.return_value = mock_inputs
        
        # Mock model generation
        mock_translated_tokens = mock.Mock()
        mock_translated_tokens.shape = (1, 10)  # Batch size 1, 10 tokens
        mock_model.generate.return_value = mock_translated_tokens
        
        # Mock tokenizer decode
        mock_tokenizer.decode.return_value = "Szia világ"
        
        # Create client and test translation
        client = MarianClient(self.config)
        result = client.translate_text("Hello world")
        
        assert result == "Szia világ"
        
        # Verify method calls
        mock_tokenizer.assert_called_with(
            "Hello world", 
            return_tensors="pt", 
            padding=True, 
            truncation=True,
            max_length=512
        )
        mock_model.generate.assert_called_once()
        mock_tokenizer.decode.assert_called_once()
    
    @mock.patch('subtitle_translator.marian_client.MarianMTModel')
    @mock.patch('subtitle_translator.marian_client.MarianTokenizer')
    @mock.patch('subtitle_translator.marian_client.torch')
    def test_translate_batch(self, mock_torch, mock_tokenizer_class, mock_model_class):
        """Test batch translation."""
        # Setup mocks similar to single translation
        mock_torch.cuda.is_available.return_value = False
        mock_torch.no_grad.return_value.__enter__ = mock.Mock()
        mock_torch.no_grad.return_value.__exit__ = mock.Mock()
        
        mock_tokenizer = mock.Mock()
        mock_model = mock.Mock()
        mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer
        mock_model_class.from_pretrained.return_value = mock_model
        mock_model.to.return_value = mock_model
        
        # Mock tokenizer behavior for batch
        mock_inputs = {"input_ids": mock.Mock(), "attention_mask": mock.Mock()}
        mock_tokenizer.return_value = mock_inputs
        
        # Mock model generation for batch (2 items)
        mock_translated_tokens = mock.Mock()
        mock_translated_tokens.shape = (2, 10)  # Batch size 2, 10 tokens each
        mock_model.generate.return_value = mock_translated_tokens
        
        # Mock tokenizer decode for each item in batch
        mock_tokenizer.decode.side_effect = ["Szia világ", "Szia mindenkinek"]
        
        # Create client and test batch translation
        client = MarianClient(self.config)
        texts = ["Hello world", "Hello everyone"]
        results = client.translate_batch(texts)
        
        assert results == ["Szia világ", "Szia mindenkinek"]
        assert len(results) == 2
    
    @mock.patch('subtitle_translator.marian_client.MarianMTModel')
    @mock.patch('subtitle_translator.marian_client.MarianTokenizer')
    @mock.patch('subtitle_translator.marian_client.torch')
    def test_translate_empty_text(self, mock_torch, mock_tokenizer_class, mock_model_class):
        """Test translation of empty text."""
        # Setup minimal mocks
        mock_torch.cuda.is_available.return_value = False
        mock_tokenizer = mock.Mock()
        mock_model = mock.Mock()
        mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer
        mock_model_class.from_pretrained.return_value = mock_model
        mock_model.to.return_value = mock_model
        
        client = MarianClient(self.config)
        result = client.translate_text("")
        
        # Empty text should be returned as-is
        assert result == ""
        
        # Tokenizer should not be called for empty text
        mock_tokenizer.assert_not_called()
    
    def test_query_model_not_supported(self):
        """Test that query_model raises NotImplementedError."""
        client = MarianClient.__new__(MarianClient)  # Create without calling __init__
        
        with pytest.raises(NotImplementedError, match="MarianMT models are specialized for translation"):
            client.query_model("What is the capital of Hungary?")


@pytest.mark.skipif(not MARIAN_AVAILABLE, reason="MarianMT dependencies not available")
class TestMarianClientIntegration:
    """Integration tests for MarianClient (require actual model download)."""
    
    def setup_method(self):
        """Set up test configuration."""
        self.config = Config(
            source_lang="en",
            target_lang="hu",
            translation_backend="marian",
            verbose=False,
            max_retries=1
        )
    
    @pytest.mark.slow
    def test_real_translation(self):
        """Test real translation with actual model (slow test)."""
        # This test will download the actual model and perform translation
        # Skip if running in CI or if you don't want to download models
        pytest.skip("Skipping real model test to avoid model download")
        
        client = MarianClient(self.config)
        result = client.translate_text("Hello world")
        
        # Just verify we get some result
        assert isinstance(result, str)
        assert len(result) > 0


class TestMarianClientWithoutDependencies:
    """Test MarianClient behavior when transformers library is not available."""
    
    @mock.patch('subtitle_translator.marian_client.TRANSFORMERS_AVAILABLE', False)
    def test_init_without_transformers(self):
        """Test that MarianClient raises ImportError when transformers is not available."""
        config = Config(translation_backend="marian")
        
        with pytest.raises(ImportError, match="Transformers library is not available"):
            MarianClient(config)


if __name__ == "__main__":
    pytest.main([__file__])
