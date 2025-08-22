# Story 09: Integrate MarianMT (Hugging Face) as Alternative Translation Backend

## Goal
Extend the subtitle translation assistant to support Hugging Face MarianMT EN↔HU model (NYTK/translation-marianmt-en-hu) as an alternative to Ollama GGUF models. Users should be able to select the backend via configuration.

## Tasks

### 1. Design & Planning
- [ ] Review current translation pipeline and config structure
- [ ] Specify config flag for backend selection (e.g. TRANSLATION_BACKEND=ollama|marian)

### 2. MarianMT Module Implementation
- [ ] Create new module/class for MarianMT backend
- [ ] Use Hugging Face transformers library
- [ ] Implement batching and error handling
- [ ] Support GPU if available, fallback to CPU
- [ ] Ensure model files are auto-downloaded/cached

### 3. Integration
- [ ] Add config flag for backend selection
- [ ] Route translation requests through selected backend
- [ ] Update main translation logic to support both backends

### 4. Testing
- [ ] Add unit tests for MarianMT backend (single and batch translation)
- [ ] Add integration tests for backend switching

### 5. Documentation
- [ ] Update README and guides to explain backend selection
- [ ] Document MarianMT setup, usage, and troubleshooting

### 6. Error Handling & Performance
- [ ] Log and handle Hugging Face API/model errors
- [ ] Optimize batching and padding for large translations

## Acceptance Criteria
- MarianMT backend works for EN↔HU translation (single and batch)
- User can select backend via config
- Ollama and MarianMT can be switched without code changes
- Tests and documentation are updated
