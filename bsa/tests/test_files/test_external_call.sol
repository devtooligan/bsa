// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;

contract TestExternalCall {
    function callExternal(address a) public {
        IA(a).hello();
    }
}

interface IA {
    function hello() external;
}