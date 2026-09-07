```python
import.Port(x) = (
	Port(x) = convert(
		Input -> "$delta_z"
		Weight -> "$abln2"
		Memory -> "tau"
	);	
	Field.state += ( Port(x) - Field.state / tau ) * dt;
	if (Port(x) in Field.range(-0.5,0.5)) {
		accept.Port(x);
		continue_action;
		return 0;
		
	} else if (Port(x) == -0.5 || Port(x) == 0.5) {
		transition.Port(x);
		continue_action;
		return 0;
		
	} else {
		reject.Port(x);
		return 1;
	}
)
```