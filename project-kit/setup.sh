#!/bin/bash

# Project Kit Setup Script
# Usage: ./setup.sh [project-name] [target-directory]

PROJECT_NAME=${1:-"my-project"}
TARGET_DIR=${2:-"."}

echo "🚀 Setting up Project Kit for: $PROJECT_NAME"
echo "   Target directory: $TARGET_DIR"
echo ""

# Create target directory if it doesn't exist
mkdir -p "$TARGET_DIR"

# Copy files
echo "📁 Copying documentation templates..."
cp CLAUDE.md "$TARGET_DIR/"
cp CHANGELOG.md "$TARGET_DIR/"
cp -r docs "$TARGET_DIR/"
cp -r .claude "$TARGET_DIR/" 2>/dev/null || mkdir -p "$TARGET_DIR/.claude/Agents" "$TARGET_DIR/.claude/commands" "$TARGET_DIR/.claude/plans"

# Copy gitignore template
if [ -f ".gitignore.template" ]; then
    cp .gitignore.template "$TARGET_DIR/.gitignore"
fi

# Replace placeholders in CLAUDE.md
echo "✏️  Customizing CLAUDE.md..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s/\[Project Name\]/$PROJECT_NAME/g" "$TARGET_DIR/CLAUDE.md"
else
    # Linux
    sed -i "s/\[Project Name\]/$PROJECT_NAME/g" "$TARGET_DIR/CLAUDE.md"
fi

# Replace in ARCHITECTURE.md
if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "s/\[Project Name\]/$PROJECT_NAME/g" "$TARGET_DIR/docs/ARCHITECTURE.md"
    sed -i '' "s/\[project-name\]/$PROJECT_NAME/g" "$TARGET_DIR/docs/ARCHITECTURE.md"
else
    sed -i "s/\[Project Name\]/$PROJECT_NAME/g" "$TARGET_DIR/docs/ARCHITECTURE.md"
    sed -i "s/\[project-name\]/$PROJECT_NAME/g" "$TARGET_DIR/docs/ARCHITECTURE.md"
fi

# Set current date in CHANGELOG
CURRENT_DATE=$(date +%Y-%m-%d)
if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "s/YYYY-MM-DD/$CURRENT_DATE/g" "$TARGET_DIR/CHANGELOG.md"
else
    sed -i "s/YYYY-MM-DD/$CURRENT_DATE/g" "$TARGET_DIR/CHANGELOG.md"
fi

echo ""
echo "✅ Project Kit setup complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Edit CLAUDE.md to add your tech stack and project details"
echo "   2. Edit docs/ARCHITECTURE.md to document your system"
echo "   3. Update CHANGELOG.md with your initial features"
echo ""
echo "📚 Files created:"
echo "   - CLAUDE.md (development guidelines)"
echo "   - CHANGELOG.md (change tracking)"
echo "   - docs/ARCHITECTURE.md (system architecture)"
echo "   - docs/features/_TEMPLATE.md (feature doc template)"
echo "   - docs/bugs/_TEMPLATE.md (bug analysis template)"
echo "   - .claude/ (Claude Code configuration)"
echo ""
