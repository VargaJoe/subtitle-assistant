#!/usr/bin/env python3
"""
Command-line tool for training custom MarianMT models for subtitle translation.
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import List

# Import directly to avoid circular dependencies with optional torch
sys.path.insert(0, str(Path(__file__).parent))
from subtitle_translator.config import Config, MarianTrainingSettings
from subtitle_translator.marian_trainer import MarianTrainer, ModelManager, TrainingDataPair


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO

    # Clear any existing handlers
    logging.getLogger().handlers.clear()

    # Create formatters
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    # Output log handler (all messages)
    output_handler = logging.FileHandler('training_output.log')
    output_handler.setLevel(logging.DEBUG)
    output_handler.setFormatter(formatter)

    # Error log handler (only warnings and above)
    error_handler = logging.FileHandler('training_error.log')
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(formatter)

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)
    logger.addHandler(output_handler)
    logger.addHandler(error_handler)


def list_models(args):
    """List all trained models."""
    manager = ModelManager(Path(args.models_dir) if args.models_dir else None)
    models = manager.list_models()
    
    if not models:
        print("No trained models found.")
        return 0
    
    print(f"\n{'='*80}")
    print(f"Trained Models ({len(models)} total)")
    print(f"{'='*80}\n")
    
    for model in models:
        print(f"📦 {model['name']}")
        print(f"   Path: {model['path']}")
        
        if model['metadata']:
            metadata = model['metadata']
            print(f"   Language: {metadata.get('source_lang', 'N/A')} → {metadata.get('target_lang', 'N/A')}")
            print(f"   Genre: {metadata.get('genre', 'N/A')}")
            print(f"   Training samples: {metadata.get('num_training_samples', 'N/A')}")
            print(f"   Base model: {metadata.get('base_model', 'N/A')}")
        print()
    
    return 0


def model_info(args):
    """Show detailed information about a model."""
    manager = ModelManager(Path(args.models_dir) if args.models_dir else None)
    info = manager.get_model_info(args.model_name)
    
    if not info:
        print(f"❌ Model not found: {args.model_name}")
        return 1
    
    print(f"\n{'='*80}")
    print(f"Model Information: {info['name']}")
    print(f"{'='*80}\n")
    
    print(f"Path: {info['path']}")
    print(f"Size: {info['size'] / (1024*1024):.2f} MB")
    
    if info['metadata']:
        print("\nTraining Details:")
        metadata = info['metadata']
        for key, value in metadata.items():
            if key != 'training_config':
                print(f"  {key}: {value}")
        
        if 'training_config' in metadata:
            print("\nTraining Configuration:")
            for key, value in metadata['training_config'].items():
                print(f"  {key}: {value}")
    
    print()
    return 0


def delete_model(args):
    """Delete a trained model."""
    manager = ModelManager(Path(args.models_dir) if args.models_dir else None)
    
    if not args.yes:
        response = input(f"Are you sure you want to delete '{args.model_name}'? (y/N): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return 0
    
    if manager.delete_model(args.model_name):
        print(f"✅ Deleted model: {args.model_name}")
        return 0
    else:
        print(f"❌ Failed to delete model: {args.model_name}")
        return 1


def train_from_srt(args):
    """Train a model from SRT file pairs."""
    # Load configuration
    config_path = Path(args.config) if args.config else Path("config.yaml")
    
    if config_path.exists():
        config = Config.from_yaml(config_path)
        print(f"✅ Loaded configuration from {config_path}")
    else:
        config = Config()
        print("⚠️  Using default configuration")
    
    # Override config with CLI arguments
    if args.source:
        config.source_lang = args.source
    if args.target:
        config.target_lang = args.target
    if args.base_model:
        config.marian_training.base_model = args.base_model
    if args.genre:
        config.marian_training.genre = args.genre
    if args.epochs:
        config.marian_training.num_epochs = args.epochs
    if args.batch_size:
        config.marian_training.batch_size = args.batch_size
    if args.learning_rate:
        config.marian_training.learning_rate = args.learning_rate
    if args.output_dir:
        config.marian_training.output_dir = args.output_dir
    
    # Parse source and target file lists
    source_files = [Path(f) for f in args.source_files]
    target_files = [Path(f) for f in args.target_files]
    
    # Verify files exist
    for f in source_files + target_files:
        if not f.exists():
            print(f"❌ File not found: {f}")
            return 1
    
    print(f"\n{'='*80}")
    print(f"Training Configuration")
    print(f"{'='*80}")
    print(f"Source language: {config.source_lang}")
    print(f"Target language: {config.target_lang}")
    print(f"Base model: {config.marian_training.base_model}")
    print(f"Genre: {config.marian_training.genre}")
    print(f"Training files: {len(source_files)} pairs")
    print(f"Epochs: {config.marian_training.num_epochs}")
    print(f"Batch size: {config.marian_training.batch_size}")
    print(f"Learning rate: {config.marian_training.learning_rate}")
    print(f"{'='*80}\n")
    
    # Initialize trainer
    trainer = MarianTrainer(config)
    
    # Prepare training data
    print("📚 Preparing training data...")
    training_data = trainer.prepare_data_from_srt_pairs(
        source_files,
        target_files,
        genre=config.marian_training.genre,
        allow_mismatched_entries=getattr(args, 'allow_mismatched_entries', False)
    )
    
    if not training_data:
        print("❌ No training data prepared. Check your SRT files.")
        return 1
    
    # Train model
    try:
        output_path = trainer.train(
            training_data,
            output_name=args.model_name,
            resume_from_checkpoint=args.resume_from if args.resume_from else None
        )
        
        print(f"\n{'='*80}")
        print(f"✅ Training Complete!")
        print(f"{'='*80}")
        print(f"Model saved to: {output_path}")
        print(f"\nTo use this model for translation, update your config.yaml:")
        print(f"  marian:")
        print(f"    model: \"{output_path}\"")
        print()
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Training failed: {e}")
        logging.error(f"Training error: {e}", exc_info=True)
        return 1


def train_from_json(args):
    """Train a model from JSON data."""
    # Load configuration
    config_path = Path(args.config) if args.config else Path("config.yaml")
    
    if config_path.exists():
        config = Config.from_yaml(config_path)
        print(f"✅ Loaded configuration from {config_path}")
    else:
        config = Config()
        print("⚠️  Using default configuration")
    
    # Override config with CLI arguments
    if args.source:
        config.source_lang = args.source
    if args.target:
        config.target_lang = args.target
    if args.base_model:
        config.marian_training.base_model = args.base_model
    if args.epochs:
        config.marian_training.num_epochs = args.epochs
    if args.batch_size:
        config.marian_training.batch_size = args.batch_size
    if args.learning_rate:
        config.marian_training.learning_rate = args.learning_rate
    if args.output_dir:
        config.marian_training.output_dir = args.output_dir
    
    # Verify JSON file exists
    json_file = Path(args.json_file)
    if not json_file.exists():
        print(f"❌ File not found: {json_file}")
        return 1
    
    print(f"\n{'='*80}")
    print(f"Training Configuration")
    print(f"{'='*80}")
    print(f"Source language: {config.source_lang}")
    print(f"Target language: {config.target_lang}")
    print(f"Base model: {config.marian_training.base_model}")
    print(f"Training data: {json_file}")
    print(f"Epochs: {config.marian_training.num_epochs}")
    print(f"Batch size: {config.marian_training.batch_size}")
    print(f"Learning rate: {config.marian_training.learning_rate}")
    print(f"{'='*80}\n")
    
    # Initialize trainer
    trainer = MarianTrainer(config)
    
    # Prepare training data
    print("📚 Loading training data...")
    training_data = trainer.prepare_data_from_json(json_file)
    
    if not training_data:
        print("❌ No training data loaded. Check your JSON file.")
        return 1
    
    # Train model
    try:
        output_path = trainer.train(
            training_data,
            output_name=args.model_name,
            resume_from_checkpoint=args.resume_from if args.resume_from else None
        )
        
        print(f"\n{'='*80}")
        print(f"✅ Training Complete!")
        print(f"{'='*80}")
        print(f"Model saved to: {output_path}")
        print(f"\nTo use this model for translation, update your config.yaml:")
        print(f"  marian:")
        print(f"    model: \"{output_path}\"")
        print()
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Training failed: {e}")
        logging.error(f"Training error: {e}", exc_info=True)
        return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Train custom MarianMT models for subtitle translation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all trained models
  python train_marian.py list
  
  # Train from SRT pairs
  python train_marian.py train-srt \\
    --source en --target hu \\
    --genre drama \\
    --source-files movie1.en.srt movie2.en.srt \\
    --target-files movie1.hu.srt movie2.hu.srt
  
  # Train from JSON data
  python train_marian.py train-json \\
    --source en --target hu \\
    --json-file training_data.json
  
  # Get model info
  python train_marian.py info marian-subtitle-en-hu-drama
  
  # Delete a model
  python train_marian.py delete marian-subtitle-en-hu-drama
"""
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--models-dir",
        help="Directory containing trained models (default: ./trained_models)"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all trained models')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Show model information')
    info_parser.add_argument('model_name', help='Name of the model')
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a trained model')
    delete_parser.add_argument('model_name', help='Name of the model to delete')
    delete_parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation')
    
    # Train from SRT command
    train_srt_parser = subparsers.add_parser('train-srt', help='Train model from SRT file pairs')
    train_srt_parser.add_argument(
        '--source-files',
        nargs='+',
        required=True,
        help='Source language SRT files'
    )
    train_srt_parser.add_argument(
        '--target-files',
        nargs='+',
        required=True,
        help='Target language SRT files (must match source files order)'
    )
    train_srt_parser.add_argument('--source', help='Source language code (e.g., en)')
    train_srt_parser.add_argument('--target', help='Target language code (e.g., hu)')
    train_srt_parser.add_argument('--genre', help='Genre label (e.g., drama, comedy, action)')
    train_srt_parser.add_argument('--base-model', help='Base MarianMT model to fine-tune')
    train_srt_parser.add_argument('--model-name', help='Custom name for the output model')
    train_srt_parser.add_argument('--epochs', type=int, help='Number of training epochs')
    train_srt_parser.add_argument('--batch-size', type=int, help='Training batch size')
    train_srt_parser.add_argument('--learning-rate', type=float, help='Learning rate')
    train_srt_parser.add_argument('--output-dir', help='Output directory for trained models')
    train_srt_parser.add_argument('--resume-from', help='Resume training from checkpoint')
    train_srt_parser.add_argument('--config', '-c', help='Configuration YAML file')
    train_srt_parser.add_argument('--allow-mismatched-entries', action='store_true', help='Allow training with SRT files that have different entry counts (uses timestamp matching)')
    
    # Train from JSON command
    train_json_parser = subparsers.add_parser('train-json', help='Train model from JSON data')
    train_json_parser.add_argument('--json-file', required=True, help='JSON file with training data')
    train_json_parser.add_argument('--source', help='Source language code (e.g., en)')
    train_json_parser.add_argument('--target', help='Target language code (e.g., hu)')
    train_json_parser.add_argument('--base-model', help='Base MarianMT model to fine-tune')
    train_json_parser.add_argument('--model-name', help='Custom name for the output model')
    train_json_parser.add_argument('--epochs', type=int, help='Number of training epochs')
    train_json_parser.add_argument('--batch-size', type=int, help='Training batch size')
    train_json_parser.add_argument('--learning-rate', type=float, help='Learning rate')
    train_json_parser.add_argument('--output-dir', help='Output directory for trained models')
    train_json_parser.add_argument('--resume-from', help='Resume training from checkpoint')
    train_json_parser.add_argument('--config', '-c', help='Configuration YAML file')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Execute command
    if args.command == 'list':
        return list_models(args)
    elif args.command == 'info':
        return model_info(args)
    elif args.command == 'delete':
        return delete_model(args)
    elif args.command == 'train-srt':
        return train_from_srt(args)
    elif args.command == 'train-json':
        return train_from_json(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
