# Based Static Analyzer (BSA)

A tool to statically analyze Solidity smart contracts, focusing on external/public functions (Entrypoints) and flattening internal/trusted contract calls for unified vulnerability analysis.

## Key Features
- Generates Abstract Syntax Trees (ASTs) using Foundry's `forge build --ast`
- Parses ASTs to extract metadata, function definitions, and call graphs
- Detects common vulnerabilities like reentrancy and arithmetic overflows
- Offers a command-line interface (CLI) to run analyses and produce reports

## Development Approach
- Built in small, modular steps with clear prompts for implementation and testing
- Uses a virtual environment for dependency management

## Final Goal
Identify Entrypoints, flatten their logic (including calls), and analyze them for vulnerabilities.# bsa
