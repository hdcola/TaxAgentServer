# 视频录制流程

1. 展示前端界面，登陆
2. 删除当前存在的spouse
3. 展示新增spouse
4. 在spouse底下新增t3 RBC
   1. 在t3 RBC中填写 box 49: $100 box 23: $1248 box 50: $5672
5. 在spouse再新增 t3 test, 然后展示删除
6. 在spouse底下新增t5 TD
   1. 在t5 TD中填写 box 24: $3520 box 10: $136 box 25: $7863
7. 在spouse再新增 t5 test, 然后展示删除
8. 在spouse底下新增t4/RL-1 john abott
   1. 在t4/RL-1 john abott填写 box 14: $59643 box 52: $123
   2. 获取一遍t4/RL-1的所有信息
   3. 在box 17A 填写 $666
9. 在spouse下新增t4/RL-1 test并展示删除
10. 获取当前有哪些tax slip
    1. 询问某一张tax slip有哪些内容
    2. 让agent解释
11. 获取有哪些家庭成员
12. 删除spouse

```text

How many family members exists in this session?

Delete john doe

How many family members exists in this session?

Add spouse alex doe

add a new t3: RBC

update t3: RBC box 49: $100, box 23: $1248, box 50: $5672

add a new t3: test

delete t3: test

add a new t5: TD

update t5: TD box 24: $3520 box 10: $136 box 25: $7863

get t5 TD detailed information and explain it in quebec french

add a new t5: test

delete t5: test

add a new t4/RL-1 john abott

update t4/RL-1 john abott box 14: $59643 

update t4/RL-1 john abott box 52: $123

get all info from t4/RL-1 john abott

How much did i earned last year from john abott?

What is my pension?

Can you modify Box 17A in t4/RL-1 john abott to 3000

add a new t4/RL-1: test

delete t4/RL-1: test

Get all detailed information form all my tax slips

Can you explain it in French and give me some advices

Summrize it in french

How many family members in this session?

Give me some advice for next year based on my current tax info
```