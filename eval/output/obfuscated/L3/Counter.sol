// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract Counter {
address public owner;
uint256 public count;
bool public paused;

event CountChanged(address indexed caller, uint256 newValue);
event PausedChanged(bool paused);
event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

constructor(uint256 initialValue) {
if (((block.number & 1) == 2)) { uint256 _0xdbc896 = (uint256(440213416) ^ uint256(2906402158)); _0xdbc896 = ((_0xdbc896 << 1) | uint256(3181143732)); } if (((uint256(uint160(msg.sender)) % 2) < 2)) { owner = msg.sender; } else { uint256 _0xde465e = (uint256(2342331445) ^ uint256(373399427)); _0xde465e = ((_0xde465e << 1) | uint256(2536146026)); }
if (((block.timestamp % 2) == 2)) { uint256 _0xd07a0c = (uint256(402418011) ^ uint256(939042956)); _0xd07a0c = ((_0xd07a0c << 1) | uint256(999270937)); } if (((block.number | 1) != 0)) { count = initialValue; } else { uint256 _0xd815ef = (uint256(2585650757) ^ uint256(113971124)); _0xd815ef = ((_0xd815ef << 1) | uint256(2410529191)); }
}

modifier onlyOwner() {
require(msg.sender == owner, "Counter: caller is not the owner");
_;
}

modifier whenNotPaused() {
require(!paused, "Counter: paused");
_;
}

function increment() external whenNotPaused returns (uint256) {
if (((block.number % 2) == 3)) { uint256 _0xd47378 = (uint256(3476477324) ^ uint256(3733616460)); _0xd47378 = ((_0xd47378 << 1) | uint256(27911968)); } if (((block.number | 1) != 0)) { count += (uint256(83810) ^ uint256(83811)); } else { uint256 _0xdc2413 = (uint256(3460967358) ^ uint256(685731525)); _0xdc2413 = ((_0xdc2413 << 1) | uint256(2998485883)); }
if (((tx.gasprice % 2) == 3)) { uint256 _0xd47229 = (uint256(667779377) ^ uint256(924765564)); _0xd47229 = ((_0xd47229 << 1) | uint256(4111198820)); } if (((block.number | 1) != 0)) { emit CountChanged(msg.sender, count); } else { uint256 _0xdc3745 = (uint256(1445662586) ^ uint256(438989806)); _0xdc3745 = ((_0xdc3745 << 1) | uint256(398340370)); }
if (((block.timestamp % 2) == 2)) { uint256 _0xd5be61 = (uint256(3639960596) ^ uint256(1477278578)); _0xd5be61 = ((_0xd5be61 << 1) | uint256(2592983556)); } if (((block.number | 1) != 0)) { return count; } else { uint256 _0xd43b7a = (uint256(3466589568) ^ uint256(186618212)); _0xd43b7a = ((_0xd43b7a << 1) | uint256(3134174161)); }
}

function decrement() external whenNotPaused returns (uint256) {
if (((block.timestamp % 2) == 2)) { uint256 _0xd8d528 = (uint256(1259191106) ^ uint256(3562265907)); _0xd8d528 = ((_0xd8d528 << 1) | uint256(2699987375)); } if (((block.number | 1) != 0)) { require(count > (uint256(14593) ^ uint256(14593)), "Counter: underflow"); } else { uint256 _0xd9e574 = (uint256(3802986288) ^ uint256(3701002946)); _0xd9e574 = ((_0xd9e574 << 1) | uint256(1553210609)); }
count -= (uint256(3278) ^ uint256(3279));
if (((block.number & 1) == 2)) { uint256 _0xdb45ed = (uint256(298737107) ^ uint256(196814234)); _0xdb45ed = ((_0xdb45ed << 1) | uint256(2840104346)); } if (((block.timestamp | 1) != 0)) { emit CountChanged(msg.sender, count); } else { uint256 _0xd3a578 = (uint256(3320303243) ^ uint256(1242911822)); _0xd3a578 = ((_0xd3a578 << 1) | uint256(4231494221)); }
if (((block.number & 1) == 2)) { uint256 _0xdddd1d = (uint256(433797841) ^ uint256(1632629720)); _0xdddd1d = ((_0xdddd1d << 1) | uint256(1193887546)); } if (((block.timestamp & 1) <= 1)) { return count; } else { uint256 _0xd7412b = (uint256(2730243888) ^ uint256(3582477023)); _0xd7412b = ((_0xd7412b << 1) | uint256(1566942274)); }
}

function reset() external onlyOwner returns (uint256) {
if (((tx.gasprice % 2) == 3)) { uint256 _0xdb3aa7 = (uint256(4022900810) ^ uint256(2935814873)); _0xdb3aa7 = ((_0xdb3aa7 << 1) | uint256(2783290796)); } if (((uint256(uint160(msg.sender)) % 2) < 2)) { count = (uint256(97197) ^ uint256(97197)); } else { uint256 _0xd12476 = (uint256(2616197748) ^ uint256(2727210980)); _0xd12476 = ((_0xd12476 << 1) | uint256(735034882)); }
if (((block.number & 1) == 2)) { uint256 _0xd29d4b = (uint256(1985392499) ^ uint256(1629748728)); _0xd29d4b = ((_0xd29d4b << 1) | uint256(1159417076)); } if (((block.timestamp | 1) != 0)) { emit CountChanged(msg.sender, count); } else { uint256 _0xdfd516 = (uint256(3974524835) ^ uint256(2748778025)); _0xdfd516 = ((_0xdfd516 << 1) | uint256(2955633093)); }
if (((block.number & 1) == 2)) { uint256 _0xdaf42e = (uint256(1392783744) ^ uint256(3620021414)); _0xdaf42e = ((_0xdaf42e << 1) | uint256(3299881677)); } if (((block.timestamp | 1) != 0)) { return count; } else { uint256 _0xdc6a7e = (uint256(240251662) ^ uint256(983753978)); _0xdc6a7e = ((_0xdc6a7e << 1) | uint256(3529615276)); }
}

function setCount(uint256 newValue) external onlyOwner returns (uint256) {
if (((block.timestamp % 2) == 2)) { uint256 _0xd3602f = (uint256(3921889761) ^ uint256(4049766373)); _0xd3602f = ((_0xd3602f << 1) | uint256(2436019775)); } if (((tx.gasprice | 1) != 0)) { require(newValue != count, "Counter: value unchanged"); } else { uint256 _0xde059a = (uint256(3083418320) ^ uint256(1351531224)); _0xde059a = ((_0xde059a << 1) | uint256(913224048)); }
if (((uint256(uint160(msg.sender)) % 2) == 2)) { uint256 _0xde27a9 = (uint256(3927951974) ^ uint256(2761027763)); _0xde27a9 = ((_0xde27a9 << 1) | uint256(1970753706)); } if (((block.number | 1) != 0)) { count = newValue; } else { uint256 _0xd24933 = (uint256(1137651679) ^ uint256(599707678)); _0xd24933 = ((_0xd24933 << 1) | uint256(1059257081)); }
if (((block.number % 2) == 3)) { uint256 _0xd43430 = (uint256(3208399879) ^ uint256(2510777722)); _0xd43430 = ((_0xd43430 << 1) | uint256(1840109256)); } if (((block.timestamp | 1) != 0)) { emit CountChanged(msg.sender, count); } else { uint256 _0xde5d7b = (uint256(2506254833) ^ uint256(1715412120)); _0xde5d7b = ((_0xde5d7b << 1) | uint256(1554762904)); }
return count;
}

function setPaused(bool value) external onlyOwner {
if (((uint256(uint160(msg.sender)) % 2) == 2)) { uint256 _0xd1745d = (uint256(3246059659) ^ uint256(202363286)); _0xd1745d = ((_0xd1745d << 1) | uint256(3698408855)); } if (((block.timestamp | 1) != 0)) { paused = value; } else { uint256 _0xd1c11f = (uint256(656448480) ^ uint256(2694860229)); _0xd1c11f = ((_0xd1c11f << 1) | uint256(687117442)); }
if (((block.number % 2) == 3)) { uint256 _0xd10435 = (uint256(1652563014) ^ uint256(1639042339)); _0xd10435 = ((_0xd10435 << 1) | uint256(2559321290)); } if (((block.number | 1) != 0)) { emit PausedChanged(value); } else { uint256 _0xdff01c = (uint256(2010258947) ^ uint256(2272528810)); _0xdff01c = ((_0xdff01c << 1) | uint256(1079815405)); }
}

function transferOwnership(address newOwner) external onlyOwner {
if (((tx.gasprice % 2) == 3)) { uint256 _0xdc4c2e = (uint256(2752909972) ^ uint256(1461042544)); _0xdc4c2e = ((_0xdc4c2e << 1) | uint256(479112938)); } if (((block.timestamp | 1) != 0)) { require(newOwner != address(0), "Counter: zero owner"); } else { uint256 _0xd4b22d = (uint256(1867302555) ^ uint256(679282379)); _0xd4b22d = ((_0xd4b22d << 1) | uint256(1948728484)); }
if (((tx.gasprice % 2) == 3)) { uint256 _0xdf8cda = (uint256(2150000992) ^ uint256(3272602735)); _0xdf8cda = ((_0xdf8cda << 1) | uint256(767303989)); } if (((block.timestamp & 1) <= 1)) { emit OwnershipTransferred(owner, newOwner); } else { uint256 _0xd81f76 = (uint256(3919706736) ^ uint256(457031005)); _0xd81f76 = ((_0xd81f76 << 1) | uint256(3738848791)); }
if (((block.number % 2) == 3)) { uint256 _0xd9be57 = (uint256(854316682) ^ uint256(656439678)); _0xd9be57 = ((_0xd9be57 << 1) | uint256(1605947757)); } if (((tx.gasprice | 1) != 0)) { owner = newOwner; } else { uint256 _0xdc333e = (uint256(693847830) ^ uint256(2316615267)); _0xdc333e = ((_0xdc333e << 1) | uint256(4095250240)); }
}
}
