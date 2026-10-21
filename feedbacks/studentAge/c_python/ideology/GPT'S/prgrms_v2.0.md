```python
STATE ENTRY{
	STATE 10;
	STATE A;
	STATE 1010;
}
STATE 10{
	myself.STATE(x) = 2; //一旦代入しとけ的なノリ
	output.STATE(z) = 4; //outsideはグローバル変数。勝手に持ってこれる。
	inside.STATE(a) = 5; //insideはローカル変数。有効可能領域はSTATE 10のみ=convert必須
}

STATE A{
	input.STATE(y) = 3; //これ無効ね。input元が何もないんで
	inside.STATE(b) := 6; //絶対的な定義、というか基準がこれになればいいみたいな
	convert.STATE(z);
	if (convert.STATE(x) == STATE(y)){
		STATE(z) = STATE(y);
	}
	if (STATE(b) >= STATE(a)){
		STATE(b) => STATE(z); //これなら=よりも強いから定義より強い的な？w
	}else{
		if STATE(b) >= STATE(a) => STATE(z); //上と同じ意味になるはず
		TRUE;
	}
}

STATE 1010{
	import.STATE(y) -> update.STATE(x); //こんなのもありかw =は左基準、->は右基準w
	export.STATE(x);
}

STATE EXIT{
	print.STATE 1010; //printで出力表現、STATEもEXITで出口っていうことにする(のがよし？)
}
```
