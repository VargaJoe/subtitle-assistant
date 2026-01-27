#!/usr/bin/env python3
"""
Simple test to verify training feature structure (without actually training).
"""

import sys
from pathlib import Path

# Test 1: Verify config can be loaded with training settings
print("Test 1: Loading config with training settings...")
try:
    from subtitle_translator.config import Config, MarianTrainingSettings
    
    config = Config()
    assert hasattr(config, 'marian_training')
    assert isinstance(config.marian_training, MarianTrainingSettings)
    assert config.marian_training.base_model == "Helsinki-NLP/opus-mt-en-hu"
    assert config.marian_training.genre == "general"
    print("✅ Config with training settings loaded successfully")
except Exception as e:
    print(f"❌ Failed to load config: {e}")
    sys.exit(1)

# Test 2: Verify training module structure
print("\nTest 2: Checking training module structure...")
try:
    from subtitle_translator.marian_trainer import TrainingDataPair, ModelManager
    
    # Test TrainingDataPair
    pair = TrainingDataPair(source="Hello", target="Szia", genre="general")
    assert pair.source == "Hello"
    assert pair.target == "Szia"
    assert pair.genre == "general"
    
    # Test ModelManager
    manager = ModelManager(Path("./trained_models"))
    assert manager.models_dir == Path("./trained_models")
    
    print("✅ Training module structure verified")
except Exception as e:
    print(f"❌ Failed to verify training module: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Verify CLI script exists
print("\nTest 3: Checking CLI script...")
try:
    train_script = Path(__file__).parent.parent.parent / "train_marian.py"
    assert train_script.exists()
    print(f"✅ CLI script exists: {train_script}")
except Exception as e:
    print(f"❌ CLI script check failed: {e}")
    sys.exit(1)

# Test 4: Verify GUI script exists
print("\nTest 4: Checking GUI script...")
try:
    gui_script = Path(__file__).parent / "train_marian_gui.ps1"
    assert gui_script.exists()
    print(f"✅ GUI script exists: {gui_script}")
except Exception as e:
    print(f"❌ GUI script check failed: {e}")
    sys.exit(1)

# Test 5: Verify documentation exists
print("\nTest 5: Checking documentation...")
try:
    doc_file = Path(__file__).parent / "docs" / "MARIANMT_TRAINING_GUIDE.md"
    assert doc_file.exists()
    print(f"✅ Documentation exists: {doc_file}")
except Exception as e:
    print(f"❌ Documentation check failed: {e}")
    sys.exit(1)

# Test 6: Verify example files exist
print("\nTest 6: Checking example files...")
try:
    example_json = Path(__file__).parent / "examples" / "training_data_example.json"
    assert example_json.exists()
    
    example_readme = Path(__file__).parent / "examples" / "README.md"
    assert example_readme.exists()
    
    print(f"✅ Example files exist")
except Exception as e:
    print(f"❌ Example files check failed: {e}")
    sys.exit(1)

print("\n" + "="*60)
print("✅ All tests passed! Training feature structure is valid.")
print("="*60)
print("\nNote: Actual training functionality requires PyTorch and")
print("Transformers libraries to be installed.")
