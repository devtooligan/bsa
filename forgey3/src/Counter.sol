// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

contract Counter {
    uint256 public number;
    address payable public owner;

    error CustomError(string message);

    constructor() {
        owner = payable(msg.sender);
    }

    function setNumber(uint256 newNumber) public {
        if (newNumber > 10) {
            revert("Number must be less than 10");
        }
        for (uint256 i = 0; i < newNumber; i++) {
            number++;
        }
    }

    function checkValue(uint256 value) public pure {
        require(value < 100, "Value too high");
        assert(value != 50);
    }
    
    function unsafeTransfer(uint256 amount) public {
        // Make an explicit external call that's easier to detect
        owner.transfer(amount);
        
        // State variable write after external call (reentrancy vulnerability)
        number = amount;
    }
    
    function testCustomError(uint256 value) public pure {
        if (value > 1000) {
            revert CustomError("Value is too large");
        }
        
        if (value < 500) {
            revert("Standard revert with value too small");
        }
        
        require(value != 750, "Cannot be exactly 750");
    }
}
