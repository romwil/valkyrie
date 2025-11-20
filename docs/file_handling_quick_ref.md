# Quick Reference: Chunked File Writing

## When to Use
- Files larger than 100 lines
- Complex SQL or JSON structures
- Files with nested quotes or special characters

## Pattern
```python
# Step 1: Create with header
with open('file.ext', 'w') as f:
    f.write('header')

# Step 2: Append sections
for section in sections:
    with open('file.ext', 'a') as f:
        f.write(section)
```

## Example from Project
See how `data/sample_data.sql` was created:
1. Header and extensions
2. Companies data
3. Jobs data  
4. Records data
5. Audit logs
6. Sample queries

Each section written separately to avoid errors.
