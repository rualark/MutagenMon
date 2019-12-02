mutagen sync terminate mushare
echo 1 > "../../mushare/mutest/conflict (1).txt"
echo 1 > "../../mushare/mutest/conflict (2).txt"
echo 1 > "../../mushare/mutest/conflict (3).txt"
echo 1 > "../../mushare/mutest/conflict (4).txt"
ssh %1 "echo 2 > /home/aark/mushare/mutest/conflict\ \(1\).txt"
ssh %1 "echo 2 > /home/aark/mushare/mutest/conflict\ \(2\).txt"
ssh %1 "echo 2 > /home/aark/mushare/mutest/conflict\ \(3\).txt"
ssh %1 "echo 2 > /home/aark/mushare/mutest/conflict\ \(4\).txt"
