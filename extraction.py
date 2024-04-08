import os
import sys
import ast
import javalang
import esprima
import subprocess

from llmCall import llm_call


def extract_functions_and_variables_python(filename):
    """
    Extracts functions and variables from a Python file.

    Args:
        filename (str): Path to the Python file.

    Returns:
        dict: A dictionary containing function names as keys and function bodies as values.
        set: A set containing variable names.
    """
    functions = {}
    variables = set()

    with open(filename, 'r') as file:
        file_content = file.read()
        tree = ast.parse(file_content, filename=filename)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                function_body = ast.get_source_segment(file_content, node)
                functions[node.name] = function_body

                # Check if the function has a decorator
                if node.decorator_list:
                    decorators = [ast.get_source_segment(file_content, decorator) for decorator in node.decorator_list]
                    functions[node.name] += '\n'.join(decorators)  # Include decorators in function body

            elif isinstance(node, ast.Name):
                variables.add(node.id)

    return functions, variables


def extract_functions_and_variables_javascript(filename):
    """
    Extracts functions and variables from a JavaScript file using esprima.

    Args:
        filename (str): Path to the JavaScript file.

    Returns:
        dict: A dictionary containing function names as keys and function bodies as values.
        set: A set containing variable names.
    """
    functions = {}
    variables = set()

    with open(filename, 'r') as file:
        file_content = file.read()
        tree = esprima.parseScript(file_content)  # Use esprima to parse JavaScript code

        for node in tree.body:
            print(node)  # Print the node object for debugging
            if node.type == 'FunctionDeclaration':
                if node.body is not None and hasattr(node.body, 'range'):  # Check if node.body has range attribute
                    function_body = file_content[node.body.range[0]:node.body.range[1]]
                    functions[node.id.name] = function_body

            elif node.type == 'VariableDeclaration':
                for declaration in node.declarations:
                    variables.add(declaration.id.name)

    return functions, variables



def extract_functions_and_variables_java(filename):
    """
    Extracts methods and variables from a Java file using javalang.

    Args:
        filename (str): Path to the Java file.

    Returns:
        dict: A dictionary containing method names as keys and method bodies as values.
        set: A set containing variable names.
    """
    functions = {}
    variables = set()

    with open(filename, 'r') as file:
        file_content = file.read()
        tree = javalang.parse.parse(file_content)

        for path, node in tree:
            if isinstance(node, javalang.tree.MethodDeclaration):
                method_body_lines = []
                for statement in node.body:
                    if isinstance(statement, javalang.tree.Statement):
                        method_body_lines.append(str(statement))
                method_body = '\n'.join(method_body_lines)
                functions[node.name] = method_body

            elif isinstance(node, javalang.tree.VariableDeclarator):
                variables.add(node.name)

    return functions, variables


def merge_all_functions(functions, module_path):
    extracted_functions = ""
    language = 'python' if module_path.endswith('.py') else 'java' if module_path.endswith('.java') else 'javascript'
    for func_name, func_body in functions.items():
        extracted_functions += func_body
        file_name = os.path.splitext(os.path.basename(module_path))[0]
        module_dir = os.path.dirname(module_path)
        module_name = os.path.basename(module_dir)
        import_module = f"{module_name}.{file_name}"
        extracted_functions += "\n"
        #print(extracted_functions)

    llm_call(extracted_functions, module_path, language, import_module)


def process_file(file_path):
    """
    Processes a single Python, Java, or JavaScript file.

    Args:
        file_path (str): Path to the Python, Java, or JavaScript file.

    Returns:
        dict: A dictionary containing all function/method names and their bodies.
        set: A set containing all variable names.
    """
    functions, variables = {}, set()
    if file_path.endswith('.py'):
        functions, variables = extract_functions_and_variables_python(file_path)
    elif file_path.endswith('.java'):
        functions, variables = extract_functions_and_variables_java(file_path)
    elif file_path.endswith('.js'):
        functions, variables = extract_functions_and_variables_javascript(file_path)

    merge_all_functions(functions, file_path)
    return functions, variables


def process_directory(directory):
    """
    Processes all Python, Java, and JavaScript files in a directory and its subdirectories.

    Args:
        directory (str): Path to the directory.

    Returns:
        dict: A dictionary containing all function/method names and their combined bodies.
        set: A set containing all variable names.
    """
    all_functions = {}
    all_variables = set()

    for root, _, files in os.walk(directory):
        # Updated the file extension check to include JavaScript files
        file_paths = [
            os.path.join(root, file_name)
            for file_name in files
            if file_name.endswith(('.py', '.java', '.js'))
        ]
        for file_path in file_paths:
            functions, variables = process_file(file_path)
            all_functions.update(functions)
            all_variables.update(variables)

    return all_functions, all_variables


def gen_test(path):
    process_directory(path)


if __name__ == "__main__":
    gen_test(sys.argv[1])