// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;


interface IA {
    function hello() external;
}


contract Vulnerable {
    mapping(address => uint) public balances;

    function deposit() public payable {
        balances[msg.sender] += msg.value;
    }


    function withdrawOutsideCall(address a) public {
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
