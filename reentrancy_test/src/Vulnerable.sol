// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

contract Vulnerable {
    mapping(address => uint) public balances;
    uint public x;  // Add a simple state variable

    function deposit() public payable {
        balances[msg.sender] += msg.value;
    }


    function hoagies(address a) public {
        uint bal = balances[msg.sender];
        
        // External call
        IA(a).hello();
        
        // State variable updates after the external call
        x = 1;   // This is a reentrancy vulnerability!
    }
    
    function safeHoagies(address a) public {
        // Read the state variables first
        uint bal = balances[msg.sender];
        
        // State variable updates first - safe pattern
        x = 1;
        
        // External call only after all state changes
        IA(a).hello();
    }

    function getBalance() public view returns (uint) {
        return address(this).balance;
    }
}

interface IA {
    function hello() external;
}
