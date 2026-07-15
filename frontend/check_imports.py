import re

with open('src/pages/DashboardsPage.js', 'r') as f:
    code = f.read()

# Find all JSX tags
tags = re.findall(r'<([A-Z][A-Za-z0-9]*)(?:\.[A-Za-z0-9]+)?\b', code)
tags = set(tags)

# Find all imports
imports = re.findall(r'import\s+.*?\{([^}]+)\}', code, re.DOTALL)
imported = set()
for imp in imports:
    for item in imp.split(','):
        item = item.strip().split(' as ')[-1] # handle 'Tooltip as RTooltip'
        if item:
            imported.add(item)

# also components defined in file
defined = re.findall(r'(?:const|function|class)\s+([A-Z][A-Za-z0-9]*)', code)
imported.update(defined)

# Destructured
imported.add('Title')
imported.add('Text')
imported.add('RangePicker')

missing = tags - imported
print("Missing:", missing)

