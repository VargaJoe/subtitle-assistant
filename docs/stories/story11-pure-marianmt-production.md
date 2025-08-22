# Story 11: Pure MarianMT Production Pipeline

## Overview
Establish MarianMT as the primary production translation backend, optimizing the entire subtitle translation workflow for maximum speed and quality using specialized neural machine translation.

## Business Value
- **Production Ready**: 40x faster processing for large-scale subtitle translation
- **Superior Quality**: Specialized neural translation optimized for EN↔HU
- **Resource Efficient**: Lower GPU memory usage, better scaling
- **Simplified Workflow**: Single-step translation without multi-model complexity

## User Story
As a subtitle translator processing large volumes of content, I want to use MarianMT as my primary translation engine, so that I can achieve maximum throughput with excellent quality for production workflows.

## Technical Approach

### Current State
- MarianMT implemented as alternative backend
- Works alongside Ollama/multi-model architecture
- Proven performance: 0.14s per entry vs 5-6s for LLM

### Proposed Enhancements

#### 1. Production Optimizations
- **Batch Processing**: Optimize batch sizes for maximum GPU utilization
- **Model Caching**: Persistent model loading across multiple files
- **Memory Management**: Efficient token handling for large subtitle files
- **Parallel Processing**: Multi-file processing capabilities

#### 2. Quality Enhancements
- **Post-Processing**: Automated quality checks and corrections
- **Format Preservation**: Enhanced subtitle timing and formatting
- **Character Name Handling**: Smart detection and preservation of proper nouns
- **Punctuation Optimization**: Hungarian-specific punctuation rules

#### 3. Workflow Integration
- **Directory Processing**: Batch process entire season directories
- **Progress Tracking**: Enhanced progress for multi-file operations
- **Error Recovery**: Robust handling of corrupted or complex subtitle files
- **Output Organization**: Automated file naming and directory structure

## Acceptance Criteria

### Performance Optimization
- [ ] Batch processing optimization for GPU utilization
- [ ] Model persistence across multiple subtitle files
- [ ] Multi-file parallel processing capability
- [ ] Memory usage optimization for large files (1000+ entries)

### Quality Assurance
- [ ] Automated post-processing quality checks
- [ ] Character name preservation (Thomas Magnum, Danny Reagan, etc.)
- [ ] Hungarian punctuation and grammar optimization
- [ ] Timing precision maintenance (±1ms accuracy)

### Production Features
- [ ] Directory batch processing: `--batch-directory`
- [ ] File pattern matching: `--pattern "*.srt"`
- [ ] Output organization: automatic `.hu.srt` naming
- [ ] Progress reporting for multi-file operations

### Integration & Documentation
- [ ] Update CLI help and documentation
- [ ] Performance benchmarking documentation
- [ ] Production workflow guide
- [ ] Troubleshooting and optimization guide

## Implementation Tasks

### Phase 1: Performance Optimization
- [ ] Implement persistent model loading
- [ ] Optimize batch size selection algorithm
- [ ] Add GPU memory monitoring and management
- [ ] Implement parallel file processing

### Phase 2: Quality Enhancement
- [ ] Build post-processing pipeline for quality improvements
- [ ] Add Hungarian-specific linguistic rules
- [ ] Implement proper noun detection and preservation
- [ ] Create automated quality validation checks

### Phase 3: Production Features
- [ ] Directory batch processing implementation
- [ ] Enhanced progress tracking for multi-file operations
- [ ] Automated output organization and naming
- [ ] Error recovery and file skipping logic

### Phase 4: Documentation & Testing
- [ ] Comprehensive production testing (full seasons)
- [ ] Performance documentation and benchmarks
- [ ] Best practices guide for production usage
- [ ] Migration path from multi-model to pure MarianMT

## Expected Impact
- **Throughput**: Process entire seasons in minutes vs hours
- **Quality**: Maintain or exceed current translation standards  
- **Reliability**: Robust production workflow for large-scale processing
- **Cost**: Reduced computational requirements vs LLM approaches

## Success Metrics
- Process Blue Bloods S14 (20+ episodes) in under 30 minutes
- Maintain translation quality scores of 90%+
- Zero manual intervention required for standard subtitle files
- 95%+ user satisfaction with translation naturalness
