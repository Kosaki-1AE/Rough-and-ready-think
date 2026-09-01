```python
＃set GND
Field[0] = (
	Element  = {};
	state    = 0.0;
	Bias     = 0.0;
	Radius   = 0.5;
	Range    = range(-0.5, 0.5);
	Boundary = {-0.5, 0.5};
	Memory   = tau;
	Token = 0;
);
distill({}, Memory) = Field.InitialBias;
spread({}, Bias, Memory) = Field.InitialRadius;

＃Local Optimization
import.Port(x, t) = (
	Current.Field = snapshot(Field[t]);

	Current.Field = convert(
		Current.Field.Element -> History
		tau -> Memory
		distill(History, Memory) -> Bias
		spread(History, Memory, Bias) -> Spread
		clamp(Spread, 0.1, 0.5) -> Radius
		range(Bias - Radius, Bias + Radius) -> Range
		{Range.min, Range.max} -> Boundary
	);

	Port(x) = convert(
		"$delta_z" -> Input
		"$abln2" -> Weight
	);

	Pending.Element = {};
	＃Global Optimization
	if (Field.Token >= 1){
		int Responsibility += 1
	}
	
	Next.Field.state =
		Current.Field.state + (
			Current.Field.Bias
			+ Port(x)
			- Current.Field.state
		) / Current.Field.Memory * dt;

	if (Next.Field.state in Current.Field.Range) {
		accept.Port(x);
		status = 0;

		Pending.Element += (
			Input  = Port(x),
			State  = Next.Field.state,
			Result = status
		);

	} else if (crossed(
		Current.Field.state,
		Next.Field.state,
		Current.Field.Boundary
	)) {
		transition.Port(x);
		status = 0;

		Pending.Element += (
			Input  = Port(x),
			State  = Next.Field.state,
			Result = status
		);

	} else {
		reject.Port(x);
		status = 1;
	}

	Field[t + 1] = commit(
		Current.Field,
		Next.Field,
		Pending.Element
	);

	return status;
);
```