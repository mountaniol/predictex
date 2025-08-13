# LangChain DuckDuckGo Provider Migration Plan

## Overview
This document outlines the plan to replace the custom DuckDuckGo provider implementation with LangChain's DuckDuckGoSearchAPIWrapper for better reliability and maintenance.

## Current Implementation Analysis

### Current Provider Features
- **Dual API approach**: Uses both DuckDuckGo instant answers API and HTML scraping
- **Async implementation**: Fully asynchronous with aiohttp
- **Result aggregation**: Combines instant answers with web search results
- **Configuration support**: Supports region, safe_search, timeout settings
- **Error handling**: Comprehensive error handling and fallback mechanisms
- **Interface compliance**: Implements SearchProvider interface with proper validation

### Current Configuration Parameters
```json
"duckduckgo": {
  "enabled": true,
  "weight": 0.7,
  "base_url": "https://api.duckduckgo.com/",
  "html_url": "https://html.duckduckgo.com/html/",
  "safe_search": "moderate",
  "region": "ru-ru",
  "timeout": 20
}
```

## LangChain Integration Strategy

### Dependencies Required
```
langchain-community>=0.0.10
duckduckgo-search>=4.0.0
```

### LangChain DuckDuckGo Features
- **Robust search**: Uses duckduckgo-search library under the hood
- **Multiple result types**: Supports text, news, images, videos, maps
- **Built-in rate limiting**: Handles rate limiting internally
- **Exception handling**: Built-in error handling
- **Maintained library**: Actively maintained by LangChain community

### Implementation Approach

#### 1. Backup Strategy
- Create backup of original `duckduckgo_provider.py` file
- Ensure rollback capability if needed

#### 2. Async Wrapper Implementation
```python
# LangChain's DuckDuckGoSearchAPIWrapper is synchronous
# Need to create async wrapper using asyncio.to_thread()
import asyncio
from functools import partial

async def async_search(self, query):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, 
        partial(self._langchain_wrapper.run, query)
    )
```

#### 3. Configuration Mapping
| Current Config | LangChain Equivalent | Notes |
|----------------|---------------------|-------|
| `safe_search` | `safesearch` | Direct mapping |
| `region` | `region` | Direct mapping |
| `timeout` | Custom wrapper | Implement using asyncio timeout |
| `max_results` | `max_results` | Direct mapping |

#### 4. Result Format Conversion
```python
# Convert LangChain results to SearchResult objects
def convert_langchain_result(self, lc_result: str, source_query: SearchQuery) -> List[SearchResult]:
    # Parse LangChain's formatted text output
    # Extract title, content, URL from formatted string
    # Create SearchResult objects maintaining compatibility
```

#### 5. Error Handling Strategy
- **Connection errors**: Retry with exponential backoff
- **Rate limiting**: Implement queue-based request management
- **Invalid responses**: Fallback to empty results with proper logging
- **Timeout handling**: Use asyncio.wait_for() for timeout control

#### 6. Feature Parity Maintenance
- **Multiple result types**: Maintain support for instant answers equivalent
- **Score calculation**: Implement relevance scoring similar to current implementation
- **Metadata preservation**: Store LangChain-specific metadata
- **URL validation**: Ensure valid URLs in results

## Implementation Steps

### Phase 1: Setup and Dependencies
1. Update `requirements.txt` with LangChain dependencies
2. Install new packages
3. Create backup of current implementation

### Phase 2: Core Implementation
1. Create new LangChain-based provider class
2. Implement async wrapper for synchronous LangChain API
3. Map configuration parameters
4. Implement result conversion logic

### Phase 3: Interface Compliance
1. Ensure SearchProvider interface compliance
2. Maintain compatibility with SearchQuery/SearchResult models
3. Implement proper error handling and validation
4. Add comprehensive logging

### Phase 4: Testing and Validation
1. Run existing test suite
2. Validate configuration compatibility
3. Test SearchRouter integration
4. Verify cache compatibility
5. Performance testing and comparison

### Phase 5: Documentation and Cleanup
1. Update documentation
2. Remove backup files (if implementation successful)
3. Update configuration examples if needed

## Risk Mitigation

### Potential Issues and Solutions

#### 1. Performance Differences
- **Risk**: LangChain wrapper might be slower than direct API calls
- **Mitigation**: Implement caching and async optimization

#### 2. Result Format Changes
- **Risk**: Different result formats might break existing functionality
- **Mitigation**: Thorough result format conversion and testing

#### 3. Configuration Incompatibility
- **Risk**: Some current config options might not be supported
- **Mitigation**: Map configs where possible, document differences

#### 4. Rate Limiting Changes
- **Risk**: Different rate limiting behavior
- **Mitigation**: Monitor and adjust rate limiting configuration

## Success Criteria

### Functional Requirements
- [ ] All existing tests pass
- [ ] SearchProvider interface fully implemented
- [ ] Configuration compatibility maintained
- [ ] Error handling equivalent or better
- [ ] Performance within acceptable range (±20% of current)

### Non-Functional Requirements
- [ ] Code maintainability improved
- [ ] Dependencies reduced (remove custom scraping code)
- [ ] Long-term sustainability ensured
- [ ] Documentation updated and accurate

## Rollback Plan

### If Implementation Fails
1. Restore original `duckduckgo_provider.py` from backup
2. Revert `requirements.txt` changes
3. Remove LangChain dependencies
4. Test system functionality restoration
5. Document issues for future reference

### Validation Criteria for Rollback
- Any critical test failures
- Performance degradation >50%
- Configuration incompatibility breaking existing setups
- Unresolvable dependency conflicts

## Timeline Estimation

- **Phase 1**: 30 minutes (setup and backup)
- **Phase 2**: 2 hours (core implementation)
- **Phase 3**: 1 hour (interface compliance)
- **Phase 4**: 1.5 hours (testing)
- **Phase 5**: 30 minutes (documentation)

**Total Estimated Time**: ~5.5 hours

## Post-Implementation Monitoring

### Key Metrics to Track
- Search success rate
- Average response time
- Cache hit ratio
- Error frequency
- Memory usage

### Monitoring Period
- Initial: 24 hours intensive monitoring
- Extended: 1 week regular monitoring
- Long-term: Include in regular system health checks

## Future Enhancements

### Potential LangChain Features to Leverage
- Advanced search types (news, images, videos)
- Better structured data extraction
- Enhanced metadata support
- Built-in result ranking and filtering
- Integration with other LangChain tools

This migration will improve the maintainability and reliability of the DuckDuckGo search provider while maintaining full compatibility with the existing search architecture.