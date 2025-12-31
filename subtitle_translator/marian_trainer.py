"""
MarianMT model trainer for subtitle-specific fine-tuning.
"""

import logging
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

try:
    from transformers import (
        MarianMTModel, 
        MarianTokenizer, 
        Trainer, 
        TrainingArguments,
        DataCollatorForSeq2Seq
    )
    import torch
    from torch.utils.data import Dataset
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    MarianMTModel = None
    MarianTokenizer = None
    Trainer = None
    TrainingArguments = None
    DataCollatorForSeq2Seq = None
    torch = None
    Dataset = None

from .config import Config, MarianTrainingSettings


logger = logging.getLogger(__name__)


@dataclass
class TrainingDataPair:
    """A pair of source and target texts for training."""
    source: str
    target: str
    genre: Optional[str] = None


class SubtitleDataset:
    """Dataset for training MarianMT models on subtitle data."""
    
    def __init__(self, data_pairs: List[TrainingDataPair], tokenizer, max_source_length: int = 128, max_target_length: int = 128):
        """
        Initialize dataset.
        
        Args:
            data_pairs: List of source-target pairs
            tokenizer: MarianTokenizer instance
            max_source_length: Maximum source sequence length
            max_target_length: Maximum target sequence length
        """
        self.data_pairs = data_pairs
        self.tokenizer = tokenizer
        self.max_source_length = max_source_length
        self.max_target_length = max_target_length
    
    def __len__(self):
        return len(self.data_pairs)
    
    def __getitem__(self, idx):
        pair = self.data_pairs[idx]
        
        # Tokenize source
        source_encoding = self.tokenizer(
            pair.source,
            max_length=self.max_source_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        # Tokenize target
        target_encoding = self.tokenizer(
            pair.target,
            max_length=self.max_target_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        # Create labels (same as target input_ids, but with padding token replaced by -100)
        labels = target_encoding['input_ids'].clone()
        labels[labels == self.tokenizer.pad_token_id] = -100
        
        return {
            'input_ids': source_encoding['input_ids'].squeeze(0),
            'attention_mask': source_encoding['attention_mask'].squeeze(0),
            'labels': labels.squeeze(0)
        }


class MarianTrainer:
    """Trainer for fine-tuning MarianMT models on subtitle-specific data."""
    
    def __init__(self, config: Config):
        """
        Initialize MarianMT trainer.
        
        Args:
            config: Configuration object with training settings
        """
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "Transformers library is not available. Install with: pip install transformers torch"
            )
        
        self.config = config
        self.training_config = config.marian_training
        self.logger = logging.getLogger(__name__)
        
        # Device configuration
        if torch is not None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.logger.info(f"Training will use: {self.device}")
        else:
            raise RuntimeError("PyTorch is not available")
        
        self.model = None
        self.tokenizer = None
    
    def prepare_data_from_srt_pairs(
        self, 
        source_srt_files: List[Path], 
        target_srt_files: List[Path],
        genre: Optional[str] = None,
        allow_mismatched_entries: bool = False
    ) -> List[TrainingDataPair]:
        """
        Prepare training data from pairs of SRT files.
        
        Args:
            source_srt_files: List of source language SRT files
            target_srt_files: List of target language SRT files
            genre: Optional genre label for the data
            allow_mismatched_entries: If True, allow files with different entry counts
                                   and match entries by timestamp overlap
            
        Returns:
            List of TrainingDataPair objects
        """
        from .srt_parser import SRTParser
        
        if len(source_srt_files) != len(target_srt_files):
            raise ValueError("Number of source and target SRT files must match")
        
        data_pairs = []
        parser = SRTParser()
        
        for source_file, target_file in zip(source_srt_files, target_srt_files):
            self.logger.info(f"Processing {source_file.name} -> {target_file.name}")
            
            # Parse both files
            source_entries = parser.parse_file(source_file)
            target_entries = parser.parse_file(target_file)
            
            if len(source_entries) != len(target_entries):
                if allow_mismatched_entries:
                    self.logger.info(
                        f"Entry count mismatch: {source_file.name} ({len(source_entries)}) "
                        f"vs {target_file.name} ({len(target_entries)}). Using timestamp matching."
                    )
                    # Match entries by timestamp overlap
                    matched_pairs = self._match_entries_by_timestamp(source_entries, target_entries)
                    self.logger.info(f"Found {len(matched_pairs)} timestamp-matched pairs")
                else:
                    self.logger.warning(
                        f"Mismatch in entry count: {source_file.name} ({len(source_entries)}) "
                        f"vs {target_file.name} ({len(target_entries)}). Skipping this pair."
                    )
                    continue
            else:
                # Exact matching for equal counts
                matched_pairs = list(zip(source_entries, target_entries))
            
            # Create training pairs from matched entries
            for source_entry, target_entry in matched_pairs:
                # Clean and prepare text
                source_text = source_entry.text.strip()
                target_text = target_entry.text.strip()
                
                if source_text and target_text:
                    data_pairs.append(TrainingDataPair(
                        source=source_text,
                        target=target_text,
                        genre=genre
                    ))
        
        self.logger.info(f"Prepared {len(data_pairs)} training pairs")
        return data_pairs
    
    def _match_entries_by_timestamp(
        self, 
        source_entries: List, 
        target_entries: List
    ) -> List[tuple]:
        """
        Match subtitle entries between source and target files based on timestamp overlap.
        
        Args:
            source_entries: List of source subtitle entries
            target_entries: List of target subtitle entries
            
        Returns:
            List of (source_entry, target_entry) tuples for matched entries
        """
        from datetime import timedelta
        
        matched_pairs = []
        tolerance = timedelta(seconds=1)  # Allow 1 second tolerance for matching
        
        # Sort entries by start time for efficient matching
        source_sorted = sorted(source_entries, key=lambda e: e.start_time)
        target_sorted = sorted(target_entries, key=lambda e: e.start_time)
        
        target_idx = 0
        
        for source_entry in source_sorted:
            # Find the best matching target entry
            best_match = None
            best_overlap = timedelta(0)
            
            # Look through target entries that could potentially match
            while target_idx < len(target_sorted):
                target_entry = target_sorted[target_idx]
                
                # If target entry starts too late, break (since lists are sorted)
                if target_entry.start_time > source_entry.end_time + tolerance:
                    break
                
                # Check for overlap
                overlap_start = max(source_entry.start_time, target_entry.start_time)
                overlap_end = min(source_entry.end_time, target_entry.end_time)
                
                if overlap_start <= overlap_end:
                    # There is overlap
                    overlap_duration = overlap_end - overlap_start
                    if overlap_duration > best_overlap:
                        best_overlap = overlap_duration
                        best_match = target_entry
                
                # If target entry ends before source starts, move to next target
                if target_entry.end_time + tolerance < source_entry.start_time:
                    target_idx += 1
                else:
                    # Target entry could still match future source entries
                    break
            
            # If we found a match with sufficient overlap, add it
            if best_match and best_overlap >= timedelta(milliseconds=500):  # At least 0.5 seconds overlap
                matched_pairs.append((source_entry, best_match))
        
        return matched_pairs
    
    def prepare_data_from_json(self, json_file: Path) -> List[TrainingDataPair]:
        """
        Load training data from JSON file.
        
        Expected format:
        [
            {"source": "Hello", "target": "Szia", "genre": "general"},
            ...
        ]
        
        Args:
            json_file: Path to JSON file
            
        Returns:
            List of TrainingDataPair objects
        """
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        data_pairs = []
        for item in data:
            data_pairs.append(TrainingDataPair(
                source=item['source'],
                target=item['target'],
                genre=item.get('genre')
            ))
        
        self.logger.info(f"Loaded {len(data_pairs)} pairs from {json_file}")
        return data_pairs
    
    def train(
        self,
        training_data: List[TrainingDataPair],
        output_name: Optional[str] = None,
        resume_from_checkpoint: Optional[str] = None
    ) -> Path:
        """
        Train a MarianMT model on subtitle data.
        
        Args:
            training_data: List of training data pairs
            output_name: Custom name for the output model
            resume_from_checkpoint: Path to checkpoint to resume from
            
        Returns:
            Path to the trained model directory
        """
        if not training_data:
            raise ValueError("Training data is empty")
        
        self.logger.info(f"Starting training with {len(training_data)} examples")
        
        # Load base model and tokenizer
        self.logger.info(f"Loading base model: {self.training_config.base_model}")
        self.tokenizer = MarianTokenizer.from_pretrained(self.training_config.base_model)
        self.model = MarianMTModel.from_pretrained(self.training_config.base_model)
        
        # Move model to device
        self.model = self.model.to(self.device)
        
        # Split data into train and validation
        split_idx = int(len(training_data) * (1 - self.training_config.validation_split))
        train_data = training_data[:split_idx]
        val_data = training_data[split_idx:]
        
        self.logger.info(f"Training samples: {len(train_data)}, Validation samples: {len(val_data)}")
        
        # Create datasets
        train_dataset = SubtitleDataset(
            train_data, 
            self.tokenizer,
            self.training_config.max_source_length,
            self.training_config.max_target_length
        )
        
        val_dataset = SubtitleDataset(
            val_data,
            self.tokenizer,
            self.training_config.max_source_length,
            self.training_config.max_target_length
        ) if val_data else None
        
        # Determine output directory
        if output_name:
            model_name = output_name
        else:
            genre_suffix = f"-{self.training_config.genre}" if self.training_config.genre != "general" else ""
            model_name = f"marian-subtitle-{self.config.source_lang}-{self.config.target_lang}{genre_suffix}"
        
        output_dir = Path(self.training_config.output_dir) / model_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Output directory: {output_dir}")
        
        # Configure training arguments
        training_args = TrainingArguments(
            output_dir=str(output_dir),
            num_train_epochs=self.training_config.num_epochs,
            per_device_train_batch_size=self.training_config.batch_size,
            per_device_eval_batch_size=self.training_config.batch_size,
            warmup_steps=self.training_config.warmup_steps,
            weight_decay=self.training_config.weight_decay,
            logging_dir=str(output_dir / "logs"),
            logging_steps=self.training_config.logging_steps,
            save_steps=self.training_config.save_steps,
            eval_steps=self.training_config.eval_steps,
            eval_strategy="steps" if val_dataset else "no",
            save_strategy="steps",
            load_best_model_at_end=True if val_dataset else False,
            metric_for_best_model="eval_loss" if val_dataset else None,
            greater_is_better=False,
            fp16=self.training_config.fp16 and self.device == "cuda",
            gradient_checkpointing=self.training_config.gradient_checkpointing,
            max_grad_norm=self.training_config.max_grad_norm,
            learning_rate=self.training_config.learning_rate,
            report_to=["tensorboard"],
            save_total_limit=3,  # Keep only 3 best checkpoints
        )
        
        # Data collator
        data_collator = DataCollatorForSeq2Seq(
            tokenizer=self.tokenizer,
            model=self.model,
            padding=True
        )
        
        # Create trainer
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            data_collator=data_collator,
            tokenizer=self.tokenizer
        )
        
        # Train
        self.logger.info("Starting training...")
        trainer.train(resume_from_checkpoint=resume_from_checkpoint)
        
        # Save final model
        self.logger.info(f"Saving model to {output_dir}")
        trainer.save_model(str(output_dir))
        self.tokenizer.save_pretrained(str(output_dir))
        
        # Save training metadata
        metadata = {
            "base_model": self.training_config.base_model,
            "source_lang": self.config.source_lang,
            "target_lang": self.config.target_lang,
            "genre": self.training_config.genre,
            "num_training_samples": len(train_data),
            "num_validation_samples": len(val_data),
            "training_config": {
                "learning_rate": self.training_config.learning_rate,
                "batch_size": self.training_config.batch_size,
                "num_epochs": self.training_config.num_epochs,
            }
        }
        
        with open(output_dir / "training_metadata.json", 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        self.logger.info("Training complete!")
        return output_dir


class ModelManager:
    """Manager for listing and managing trained MarianMT models."""
    
    def __init__(self, models_dir: Optional[Path] = None):
        """
        Initialize model manager.
        
        Args:
            models_dir: Directory containing trained models (default: ./trained_models)
        """
        self.models_dir = models_dir or Path("./trained_models")
        self.logger = logging.getLogger(__name__)
    
    def list_models(self) -> List[Dict]:
        """
        List all trained models.
        
        Returns:
            List of dictionaries with model information
        """
        if not self.models_dir.exists():
            return []
        
        models = []
        for model_dir in self.models_dir.iterdir():
            if not model_dir.is_dir():
                continue
            
            # Check if it's a valid model directory
            if not (model_dir / "config.json").exists():
                continue
            
            # Load metadata if available
            metadata_file = model_dir / "training_metadata.json"
            metadata = {}
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            
            models.append({
                "name": model_dir.name,
                "path": str(model_dir),
                "metadata": metadata
            })
        
        return models
    
    def get_model_info(self, model_name: str) -> Optional[Dict]:
        """
        Get detailed information about a specific model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Dictionary with model information or None if not found
        """
        model_dir = self.models_dir / model_name
        if not model_dir.exists():
            return None
        
        metadata_file = model_dir / "training_metadata.json"
        metadata = {}
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        
        return {
            "name": model_name,
            "path": str(model_dir),
            "metadata": metadata,
            "size": self._get_dir_size(model_dir)
        }
    
    def _get_dir_size(self, path: Path) -> int:
        """Get total size of directory in bytes."""
        total = 0
        for item in path.rglob('*'):
            if item.is_file():
                total += item.stat().st_size
        return total
    
    def delete_model(self, model_name: str) -> bool:
        """
        Delete a trained model.
        
        Args:
            model_name: Name of the model to delete
            
        Returns:
            True if successful, False otherwise
        """
        model_dir = self.models_dir / model_name
        if not model_dir.exists():
            self.logger.warning(f"Model not found: {model_name}")
            return False
        
        try:
            import shutil
            shutil.rmtree(model_dir)
            self.logger.info(f"Deleted model: {model_name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete model {model_name}: {e}")
            return False
