# Documentation Command

Generate or update documentation for code, APIs, or features.

## Usage

```
/docs [file-path]           # Generate docs for file
/docs api [endpoint]        # Document API endpoint
/docs feature [name]        # Create feature documentation
/docs changelog [change]    # Add changelog entry
```

## Documentation Types

### Code Documentation
- Function/method descriptions
- Parameter explanations
- Return value documentation
- Usage examples

### API Documentation
- Endpoint description
- Request/response format
- Authentication requirements
- Error responses
- Examples

### Feature Documentation
Generate `docs/features/[feature-name].md` with:
- Overview
- User stories
- Architecture
- Usage
- Testing

### Changelog Entry
Add to CHANGELOG.md with:
- Date
- Category (Added/Changed/Fixed/Removed)
- Description
- Related files

## Output Format

Follow project documentation style:
- Use clear, concise language
- Include code examples
- Reference related documentation
- Update ARCHITECTURE.md if structure changes
