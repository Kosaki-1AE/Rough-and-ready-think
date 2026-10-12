1. 目的

Loom Core は、特定のプログラミング言語ではなく、

状態・条件・遷移・保留・観測

を共通形式で表現するための基準記述である。

C、COBOL、Markdown、自然言語などは、Loom Core が持つ同じ意味を異なる記法で表現したものとして扱う。

⸻

2. 基本モデル

すべての処理を次の流れとして考える。

STATE
  ↓
?!
  ↓
CONDITION
  ↓
AND / OR / XOR / NOT
  ↓
* または /
  ↓
NEXT STATE

⸻

3. STATE

STATE は現在確定している状態。

STATE 0000

4bitを使用する場合、

0000 ～ 1111

の16状態を基本状態空間とする。

STATEそのものと、STATE間の遷移は分離して扱う。

⸻

4. ?!

?! は Observe。

現在の状態を見る。

STATE 0010
?!

?! 自体は状態を変更しない。

⸻

5. AND

AND は複数条件がすべて成立しているかを見る。

A AND B

意味：

A = true
B = true
↓
transition enabled

ANDそのものは遷移を実行しない。

AND = 行ける

であり、

/ = 行った

とは区別する。

⸻

6. OR

OR は複数条件のうち、少なくとも1つが成立しているかを見る。

A OR B
A または B
↓
transition enabled

⸻

7. XOR

XOR は条件同士の差を検出する。

A XOR B

2値の場合、

同じ     → 0
異なる   → 1

とする。

将来的には状態間の差・距離を表す演算へ拡張可能。

⸻

8. NOT

NOT は状態または条件を反転する。

NOT A
0 → 1
1 → 0

⸻

9. *

* は Suspend。

成立しているが、まだ確定しない。

A AND B *

意味：

条件成立
↓
遷移可能
↓
保留

* は可能性を現在のSTATEから分離して保持する。

⸻

10. /

/ は Transition / Commit。

可能なものを実際の状態へ確定する。

A AND B / NEXT

意味：

A AND B
↓
成立
↓
/
↓
STATE = NEXT

したがって、

AND/
OR/
XOR/
NOT/

は「判定＋即時遷移」の省略表現として扱える。

⸻

11. /* */

/* ... */ は Suspend Region。

/*
この領域は現在の実行対象ではない
*/

単なる文章コメントとしてだけでなく、

現在の作用世界から一時的に外された領域

として解釈する。

⸻

12. 基本遷移

STATE 0000
A AND B / 1000

内部的には、

OBSERVE STATE
CONDITION:
    AND(A, B)
IF ENABLED:
    TRANSITION 0000 -> 1000

と同義。

⸻

13. 保留を含む遷移

A AND B *

この時点ではSTATEは変わらない。

その後、

/

が与えられた場合に保留中の遷移を確定する。

A AND B *
?!
/

は、

条件成立
↓
保留
↓
現在を観測
↓
遷移確定

を意味する。

⸻

14. 4bit Transition

4bitは主に遷移表現に使用する。

0000 / 1000

は、

0000
↓
1000

への確定遷移。

例：

0000 AND/ 1000
0001 OR/  0101
0010 XOR/ 0110

⸻

15. 共通意味表現

すべての記法は最終的に次の概念へ変換する。

STATE
OBSERVE
CONDITION
AND
OR
XOR
NOT
SUSPEND
TRANSITION
RELATION

これをLoom Coreの意味層とする。

⸻

16. C表現例

Loom：

A AND B / NEXT

C：

if (A && B) {
    state = NEXT;
}

⸻

17. COBOL表現例

Loom：

A AND B / NEXT

COBOL：

IF A AND B
    MOVE NEXT TO STATE
END-IF

⸻

18. Markdown表現例

Loom：

A AND B / NEXT

Markdown：

AとBの両方が成立した場合、状態をNEXTへ遷移させる。

⸻

19. 原則

Loom Coreでは、

記法 ≠ 意味

とする。

C、COBOL、Markdown、Loomは異なる見た目を持つが、

A AND B / NEXT

という意味構造は共通である。

したがって変換時には、

C
 ↓
Loom Core
 ↓
COBOL

のように、直接言語間変換するのではなく、

一度意味へ戻してから別の記法へ変換する。

⸻

20. 最小コア

Loom Core v0.1 で必須とするものは以下だけとする。

STATE
?!
AND
OR
XOR
NOT
*
/
/* */

それ以外の構文は、このコアから必要に応じて派生させる。