// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

contract Vulnerable {
    mapping(address => uint) public balances;

    function deposit() public payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw() public {
        uint bal = balances[msg.sender];
        require(bal > 0);
        
        // Vulnerability: external call before state variable update
        (bool sent, ) = msg.sender.call{value: bal}("");
        require(sent, "Failed to send Ether");
        
        // State variable update after the external call
        balances[msg.sender] = 0;
    }

    function hoagies() public {
        uint bal = balances[msg.sender];
        msg.sender.call{value: bal}("");
        
        // State variable update after the external call
        balances[msg.sender] = 10;
        // State variable update after the external call
        
    }

    function hoagiesOUTSIDECALL(address a) public {
        uint bal = balances[msg.sender];
        IA(a).hello();
        
        // State variable update after the external call
        balances[msg.sender] = 10;
        // State variable update after the external call
        balances[msg.sender] = 0;
    }

    function getBalance() public view returns (uint) {
        return address(this).balance;
    }
}

interface IA {
    function hello() external;
}
