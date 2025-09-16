#!/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo
echo -e "${CYAN}=====================================${NC}"
echo -e "${CYAN}   FormAI - Automation Test Suite${NC}"
echo -e "${CYAN}=====================================${NC}"
echo

# Check if FormAI is running
if ! curl -f http://localhost:5003/api/health &> /dev/null; then
    echo -e "${RED}[ERROR] FormAI is not running!${NC}"
    echo "Please run './start.sh' first."
    exit 1
fi

echo -e "${GREEN}FormAI is running. Starting tests...${NC}"
echo

# Test 1: RoboForm test page
echo -e "${YELLOW}[TEST 1] RoboForm comprehensive form...${NC}"
curl -X POST "http://localhost:5003/api/automation/start" \
     -H "Content-Type: application/json" \
     -d '{"profile":"koodos","urls":["https://www.roboform.com/filling-test-all-fields"],"headless":true}'
echo
sleep 5

# Test 2: Generic contact form
echo -e "${YELLOW}[TEST 2] Generic contact form...${NC}"
curl -X POST "http://localhost:5003/api/automation/start" \
     -H "Content-Type: application/json" \
     -d '{"profile":"koodos","urls":["https://www.w3schools.com/html/html_forms.asp"],"headless":true}'
echo
sleep 5

# Test 3: Multiple URLs at once
echo -e "${YELLOW}[TEST 3] Multiple URLs batch processing...${NC}"
curl -X POST "http://localhost:5003/api/automation/start" \
     -H "Content-Type: application/json" \
     -d '{"profile":"koodos","urls":["https://example.com","https://google.com"],"headless":true}'
echo
sleep 5

# Check automation status
echo
echo -e "${BLUE}Checking automation status...${NC}"
curl http://localhost:5003/api/automation/status
echo
echo

echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}   Test Results${NC}"
echo -e "${GREEN}=====================================${NC}"
echo
echo -e "${GREEN}✅ All automation tests completed!${NC}"
echo
echo "Check the logs for detailed results:"
echo "  docker-compose logs -f"
echo
echo "You can also check:"
echo "  - Screenshots: ./screenshots/"
echo "  - Recordings: ./recordings/"
echo "  - Profiles: ./profiles/"
echo