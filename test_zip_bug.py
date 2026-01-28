#!/usr/bin/env python3
"""
Test zip() behavior with mismatched list lengths.
"""

def test_zip_mismatch():
    print("Testing zip() with mismatched lengths:\n")
    
    entries = ["Entry1", "Entry2", "Entry3"]
    translations = ["Trans1", "Trans2"]  # ONE MISSING!
    
    print(f"Entries: {entries} ({len(entries)} items)")
    print(f"Translations: {translations} ({len(translations)} items)")
    print()
    
    print("Result of zip():")
    result = list(zip(entries, translations))
    for entry, trans in result:
        print(f"  {entry} -> {trans}")
    
    print()
    print(f"❌ CRITICAL: Entry3 was SILENTLY DROPPED!")
    print(f"   zip() truncated to shorter list length")
    print(f"   Entry3 will appear with NO TRANSLATION or WRONG TEXT")


if __name__ == "__main__":
    test_zip_mismatch()
