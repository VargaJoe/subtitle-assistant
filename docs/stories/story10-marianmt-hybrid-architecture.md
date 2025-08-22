# Story 10: MarianMT Hybrid Multi-Model Architecture

## Overview
Integrate MarianMT as the **Translation Model** within our existing multi-model pipeline, combining the speed and quality of specialized neural translation with the context awareness and validation capabilities of LLMs.

## Business Value
- **Best of Both Worlds**: Specialized translation quality + contextual intelligence
- **Performance**: 40x faster core translation while maintaining multi-model benefits
- **Quality**: Superior translation with character consistency and technical validation
- **Flexibility**: Option to use pure MarianMT (fast) or hybrid (comprehensive)

## User Story
As a subtitle translator, I want to leverage MarianMT's superior translation speed and quality within the multi-model pipeline, so that I get fast, high-quality translations with context awareness and validation.

## Technical Approach

### Current Multi-Model Pipeline
1. **Context Model** (llama3.2): Story analysis, character profiling
2. **Translation Model** (gemma3): Primary translation ← REPLACE WITH MARIANMT
3. **Technical Validator** (gemma3:12b): Quality validation
4. **Dialogue Specialist** (gemma3): Character voice consistency

### Proposed Hybrid Architecture
1. **Context Model** (llama3.2): Story analysis, character profiling
2. **Translation Model** (MarianMT): Fast, high-quality base translation
3. **Context Enhancer** (gemma3): Apply story context to MarianMT output
4. **Technical Validator** (gemma3:12b): Quality validation
5. **Dialogue Specialist** (gemma3): Character voice consistency

## Acceptance Criteria

### Core Integration
- [ ] MarianMT replaces Translation Model in multi-model pipeline
- [ ] Context Model output passed to Context Enhancer for refinement
- [ ] Technical Validator validates MarianMT + context output
- [ ] Dialogue Specialist refines character voices
- [ ] Performance improvement: 10-20x faster than current pipeline

### Configuration
- [ ] New mode: `--backend hybrid` (MarianMT + multi-model)
- [ ] Existing modes preserved: `--backend ollama`, `--backend marian`
- [ ] Step selection works: `--steps translation,validation`
- [ ] Context enhancement can be disabled: `--no-context-enhancement`

### Quality Assurance
- [ ] Translation quality equals or exceeds pure MarianMT
- [ ] Character consistency maintained through Dialogue Specialist
- [ ] Technical validation catches errors MarianMT might miss
- [ ] Story context integration improves naturalness

### Documentation
- [ ] Update Multi-Model Architecture Guide
- [ ] Add Hybrid Mode section to README
- [ ] Performance comparison matrix updated
- [ ] Best practices for hybrid usage

## Implementation Tasks

### Phase 1: Core Integration
- [ ] Create `HybridMultiModelOrchestrator` class
- [ ] Modify `multi_model.py` to support MarianMT as Translation Model
- [ ] Implement Context Enhancer step (lightweight LLM refinement)
- [ ] Update configuration system for hybrid mode

### Phase 2: Pipeline Enhancement
- [ ] Integrate MarianMT output into validation pipeline
- [ ] Ensure Dialogue Specialist works with MarianMT base translations
- [ ] Implement step selection for hybrid mode
- [ ] Add performance monitoring and metrics

### Phase 3: Testing & Documentation
- [ ] Comprehensive testing with sample files
- [ ] Performance benchmarking vs pure modes
- [ ] Update all documentation
- [ ] Create migration guide for existing users

## Expected Performance
- **Speed**: 10-20x faster than current multi-model (vs 40x pure MarianMT)
- **Quality**: Superior to both pure MarianMT and pure LLM
- **Features**: Full context awareness + specialized translation

## Risk Assessment
- **Low Risk**: MarianMT already proven to work excellently
- **Integration Complexity**: Moderate - requires pipeline architecture changes
- **Testing Overhead**: High - need to validate quality across all use cases
