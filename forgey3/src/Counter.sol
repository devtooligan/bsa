// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

contract Counter {
    uint256 public number;

    function setNumber(uint256 newNumber) public {
        if (newNumber > 10) {
            revert("Number must be less than 10");
        }
        for (uint256 i = 0; i < newNumber; i++) {
            number++;
        }
    }

}
