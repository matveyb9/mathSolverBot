import re
import math
import cmath
from dataclasses import dataclass
from typing import Optional
from sympy import (
    symbols, solve, Eq, simplify, expand, factor,
    sqrt, Rational, latex, sympify, Symbol,
    linsolve, nonlinsolve, S, oo, zoo, nan,
    parse_expr, I, re as sym_re, im as sym_im
)
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations,
    implicit_multiplication_application, convert_xor
)
import sympy


@dataclass
class EquationResult:
    equation_type: str
    original: str
    normalized: str
    coefficients: dict
    solutions: list
    solution_text: str
    steps: list


TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)


def preprocess_equation(raw: str) -> str:
    """Clean and normalize input string."""
    eq = raw.strip()
    eq = eq.replace("−", "-").replace("–", "-").replace("×", "*").replace("÷", "/")
    eq = eq.replace("^", "**")
    eq = re.sub(r'\s+', '', eq)
    return eq


def detect_variables(expr_str: str) -> list:
    """Detect all variable names in expression."""
    tokens = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', expr_str)
    skip = {'sin', 'cos', 'tan', 'log', 'exp', 'sqrt', 'pi', 'e', 'E',
            'ln', 'abs', 'asin', 'acos', 'atan', 'I', 'oo'}
    return list(dict.fromkeys(t for t in tokens if t not in skip))


def parse_and_solve(raw: str) -> EquationResult:
    """Main entry point: parse equation string and solve it."""
    eq_str = preprocess_equation(raw)

    # Detect if it's an equation (has =) or expression (= 0 implied)
    if '=' in eq_str:
        parts = eq_str.split('=', 1)
        lhs_str, rhs_str = parts[0], parts[1]
    else:
        lhs_str = eq_str
        rhs_str = '0'

    var_names = detect_variables(lhs_str + rhs_str)
    if not var_names:
        raise ValueError("Не найдено переменных в уравнении.")

    # Create sympy symbols
    syms = {name: symbols(name) for name in var_names}

    try:
        lhs = parse_expr(lhs_str, local_dict=syms, transformations=TRANSFORMATIONS)
        rhs = parse_expr(rhs_str, local_dict=syms, transformations=TRANSFORMATIONS)
    except Exception as e:
        raise ValueError(f"Не удалось разобрать выражение: {e}")

    diff = expand(lhs - rhs)

    # Determine primary variable (prefer x, then first found)
    if 'x' in syms:
        main_var = syms['x']
    elif 'y' in syms and len(var_names) == 1:
        main_var = syms['y']
    else:
        main_var = syms[var_names[0]]

    eq_type, coeffs, steps = classify_equation(diff, main_var, syms)

    # Solve
    try:
        solutions_raw = solve(Eq(lhs, rhs), list(syms.values()) if len(syms) > 1 else main_var)
    except Exception as e:
        raise ValueError(f"Не удалось решить уравнение: {e}")

    solutions, sol_text = format_solutions(solutions_raw, main_var, var_names)

    normalized = f"{diff} = 0" if diff != lhs - rhs else f"{lhs} = {rhs}"

    return EquationResult(
        equation_type=eq_type,
        original=raw.strip(),
        normalized=str(Eq(lhs, rhs)),
        coefficients=coeffs,
        solutions=solutions,
        solution_text=sol_text,
        steps=steps,
    )


def classify_equation(diff, main_var, syms) -> tuple:
    """Classify equation type and extract coefficients."""
    from sympy import degree, Poly, LC, groebner
    coeffs = {}
    steps = []

    var_names = list(syms.keys())

    # System of equations is handled separately
    if len(syms) > 1:
        eq_type = f"Уравнение с {len(syms)} переменными ({', '.join(var_names)})"
        return eq_type, coeffs, steps

    try:
        poly = sympy.Poly(diff, main_var)
        deg = poly.degree()
        poly_coeffs = poly.all_coeffs()
    except sympy.PolynomialError:
        # Transcendental
        eq_type = detect_transcendental_type(diff, main_var)
        return eq_type, {}, []

    if deg == 1:
        eq_type = "Линейное уравнение (1-й степени)"
        a = poly_coeffs[0]
        b = poly_coeffs[1] if len(poly_coeffs) > 1 else 0
        coeffs = {'a (при x)': str(a), 'b (свободный член)': str(b)}
        steps = [
            f"Приводим к виду: ax + b = 0",
            f"a = {a}, b = {b}",
            f"x = -b/a = {sympy.Rational(-b, a) if a != 0 else '∞'}",
        ]

    elif deg == 2:
        eq_type = "Квадратное уравнение (2-й степени)"
        a = poly_coeffs[0]
        b = poly_coeffs[1] if len(poly_coeffs) > 1 else 0
        c = poly_coeffs[2] if len(poly_coeffs) > 2 else 0
        D = b**2 - 4*a*c
        coeffs = {
            'a (при x²)': str(a),
            'b (при x)': str(b),
            'c (свободный член)': str(c),
            'D (дискриминант)': str(sympy.simplify(D)),
        }
        steps = [
            f"Приводим к виду: ax² + bx + c = 0",
            f"a = {a}, b = {b}, c = {c}",
            f"D = b² - 4ac = ({b})² - 4·({a})·({c}) = {sympy.simplify(D)}",
        ]
        if D > 0:
            steps.append("D > 0 → два различных вещественных корня")
        elif D == 0:
            steps.append("D = 0 → один корень (кратный)")
        else:
            steps.append("D < 0 → комплексные корни")

    elif deg == 3:
        eq_type = "Кубическое уравнение (3-й степени)"
        a = poly_coeffs[0]
        b = poly_coeffs[1] if len(poly_coeffs) > 1 else 0
        c = poly_coeffs[2] if len(poly_coeffs) > 2 else 0
        d = poly_coeffs[3] if len(poly_coeffs) > 3 else 0
        coeffs = {
            'a (при x³)': str(a),
            'b (при x²)': str(b),
            'c (при x)': str(c),
            'd (свободный член)': str(d),
        }
        steps = [
            f"Приводим к виду: ax³ + bx² + cx + d = 0",
            f"a={a}, b={b}, c={c}, d={d}",
            "Решаем методом Кардано или численно",
        ]

    elif deg == 4:
        eq_type = "Уравнение 4-й степени (биквадратное или общее)"
        coeffs = {f'коэф. при x^{deg-i}': str(poly_coeffs[i]) for i in range(len(poly_coeffs))}
        steps = ["Приводим к виду: ax⁴ + bx³ + cx² + dx + e = 0"]

    elif deg == 0:
        eq_type = "Тождество / Противоречие (нет переменной)"
        return eq_type, {}, ["Уравнение не содержит переменных."]

    else:
        eq_type = f"Многочленное уравнение {deg}-й степени"
        coeffs = {f'x^{deg-i}': str(poly_coeffs[i]) for i in range(len(poly_coeffs))}
        steps = [f"Степень многочлена: {deg}"]

    return eq_type, coeffs, steps


def detect_transcendental_type(diff, var) -> str:
    """Detect transcendental equation type."""
    expr_str = str(diff)
    if 'sin' in expr_str or 'cos' in expr_str or 'tan' in expr_str:
        return "Тригонометрическое уравнение"
    if 'exp' in expr_str or 'E**' in expr_str:
        return "Показательное уравнение"
    if 'log' in expr_str or 'ln' in expr_str:
        return "Логарифмическое уравнение"
    if 'sqrt' in expr_str or '**(' in expr_str:
        return "Иррациональное уравнение"
    return "Трансцендентное уравнение"


def format_solutions(solutions_raw, main_var, var_names: list) -> tuple:
    """Format solutions into readable strings."""
    if solutions_raw is None or solutions_raw == []:
        return [], "❌ Решений нет"

    if solutions_raw is True or solutions_raw == S.true:
        return ["∞"], "♾️ Бесконечно много решений (тождество)"

    if solutions_raw is False or solutions_raw == S.false:
        return [], "❌ Нет решений (противоречие)"

    solutions = []
    lines = []

    # Handle list of tuples (multi-variable)
    if isinstance(solutions_raw, list) and solutions_raw and isinstance(solutions_raw[0], tuple):
        for i, sol_tuple in enumerate(solutions_raw, 1):
            parts = [f"{var_names[j]} = {sympy.simplify(v)}" for j, v in enumerate(sol_tuple)]
            line = ", ".join(parts)
            lines.append(f"  Решение {i}: {line}")
            solutions.append(line)
        return solutions, "\n".join(lines)

    # Single variable solutions
    for i, sol in enumerate(solutions_raw, 1):
        s = sympy.simplify(sol)
        # Try to get decimal approximation
        try:
            val = complex(s)
            if val.imag == 0:
                approx = f" ≈ {val.real:.6g}" if val.real != int(val.real) else ""
                sol_str = f"{s}{approx}"
            else:
                sol_str = f"{s} (комплексное)"
        except Exception:
            sol_str = str(s)

        lines.append(f"  x{_sub(i)} = {sol_str}")
        solutions.append(str(s))

    if not lines:
        return [], "❌ Решений нет"

    return solutions, "\n".join(lines)


def _sub(n: int) -> str:
    """Return subscript digit."""
    subs = "₀₁₂₃₄₅₆₇₈₉"
    return subs[n] if n < 10 else str(n)


def format_result_message(result: EquationResult) -> str:
    """Format full result as Telegram message (MarkdownV2-safe plain text)."""
    lines = [
        f"📐 Уравнение: {result.original}",
        f"📊 Тип: {result.equation_type}",
        "",
    ]

    if result.coefficients:
        lines.append("🔢 Коэффициенты:")
        for k, v in result.coefficients.items():
            lines.append(f"  • {k} = {v}")
        lines.append("")

    if result.steps:
        lines.append("📝 Шаги решения:")
        for step in result.steps:
            lines.append(f"  {step}")
        lines.append("")

    lines.append("✅ Ответ:")
    lines.append(result.solution_text)

    return "\n".join(lines)
