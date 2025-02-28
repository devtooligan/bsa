// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

contract LoopTest {
    uint256 public sum;
    
    // Simple for loop example
    function forLoopSum(uint256 n) public {
        uint256 total = 0;
        
        for (uint256 i = 0; i < n; i++) {
            total += i;
        }
        
        sum = total;
    }
    
    // Simple while loop example
    function whileLoopSum(uint256 n) public {
        uint256 total = 0;
        uint256 i = 0;
        
        while (i < n) {
            total += i;
            i++;
        }
        
        sum = total;
    }
    
    // Loop with conditional inside
    function conditionalLoop(uint256 n) public {
        uint256 total = 0;
        
        for (uint256 i = 0; i < n; i++) {
            if (i % 2 == 0) {
                total += i * 2;
            } else {
                total += i;
            }
        }
        
        sum = total;
    }
}