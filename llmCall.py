import requests
import os
from openai import OpenAI


def llm_call(code_body, module_path, language, import_module):
    """
    Makes a call to the OpenAI API with the code body.

    Args:
        code_body (str): The body of the code to be passed to the OpenAI API.
        module_path (str): The path of the module.
        import_module (str): module of the app.
        language (str): The programming language of the code ('python' or 'java').
    """
    # Set your OpenAI API key
    api_key = os.getenv('API_KEY')

    runTestPython = """
        def suite():
            loader = unittest.TestLoader()
            test_suite = loader.loadTestsFromTestCase(className)
            return test_suite

        if __name__ == '__main__':
            runner = unittest.TextTestRunner()
            runner.run(suite())
    """

    runTestJava = """
        import org.junit.runner.JUnitCore;
        import org.junit.runner.Result;
        import {import_module}
        import org.junit.runner.notification.Failure;

        public class RunTests {
            public static void main(String[] args) {
                Result result = JUnitCore.runClasses(className.class);
                for (Failure failure : result.getFailures()) {
                    System.out.println(failure.toString());
                }
                System.out.println(result.wasSuccessful());
            }
        }
    """
    runTestJavascript = """
            // Test runner for JavaScript
            const { exec } = require('child_process');
            const fs = require('fs');

            fs.writeFileSync('./temp.js', code);

            exec('node ./temp.js', (error, stdout, stderr) => {
                if (error) {
                    console.error('Error:', error.message);
                    return;
                }
                console.log(stdout);
            });
        """

    # Determine which runTest code to use based on the language
    if language == 'python':
        runTest = runTestPython
    elif language == 'java':
        runTest = runTestJava
    elif language == 'javascript':
        runTest = runTestJavascript
    else:
        raise ValueError(f"Unsupported language: {language}")

    # Set the prompt text for the API call
    prompt = f"""
# Java Test Case Generation

## Objective:
Generate test cases for the provided function to ensure its correctness and reliability.

## Code to Test:
```java
{code_body}

Requirements:
- Ensure that the test class name matches the class under test exactly for both the Java code and the corresponding test case.
- For the given Java code, the test class should be named same as file name.
- Return only test cases including all necessary import statements with the module {import_module}.
- use the same method name that is used in the above code, donot use any other method.
- donot miss the method body in each method you define.
- Always organize test cases using Java classes.
- use the necessary imports and especially import {import_module} in the testcase file.
- Below code serves as an example to run the test cases, where className is the appropriate class for the language.:
        {runTest}
- do not include any extra keywords in the code. Generated it as a professional code ready to test.

Guidelines:
- Always mock dependencies using libraries like Mockito to isolate the code under test.
- Set up mock objects using @Before or @BeforeEach methods to ensure they are properly configured before each test method.
- Utilize JUnit assertions like assertEquals, assertTrue, assertFalse, etc., to validate expected behavior.
- Use parameterized tests where applicable to cover various input scenarios.
- Ensure the test cases are well-structured, readable, and adhere to best practices.

Notes:
- Your generated test cases should cover various scenarios, including edge cases.
- Ensure the test cases are well-structured, readable, and adhere to best practices.
- generate 10 testcases mainly with method body and functionalities.
- only use junit package except this dont use any other package.
- Also import all the used packages in the code , dont miss any of the import.
"""
    # print(prompt)
    try:
        # Make the API call
        client = OpenAI(api_key=api_key)
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an IT software Engineer. You are developing an application."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.1
        )

        # Extract the response content
        response_content = completion.choices[0].message.content

        # Extract and write the code to a file
        extracted_code = extract_code(response_content, language)
        write_code_to_file(module_path, extracted_code, language)

    except requests.exceptions.HTTPError as err:
        print("Error:", err)


def extract_code(response_content, language):
    """
    Extracts code block from the response content.

    Args:
        response_content (str): The content of the response from OpenAI.
        language (str): The programming language of the code ('python', 'java', or 'javascript').

    Returns:
        str: The extracted code block.
    """
    # Split the content by newlines
    lines = response_content.split('\n')

    # Initialize lists to store import statements, class/function definitions, and other code lines
    import_statements = []
    code_lines = []

    # Flags to indicate whether we are inside a class or function definition
    inside_class = False
    inside_function = False

    # Iterate over each line in the response content
    for line in lines:
        # Check if the line starts with 'import' or 'from' (for Python/Java) or 'require' (for JavaScript)
        if line.startswith(('import', 'from')) or (language == 'java' and line.strip().startswith('import')) or (
                language == 'javascript' and line.strip().startswith('require')):
            import_statements.append(line)
        # Check if the line starts with 'class' (for Python/Java) or 'function' (for JavaScript)
        elif line.startswith('class') or (language in ('java', 'javascript') and line.strip().startswith('class')):
            code_lines.append(line)
            inside_class = True
        # Check if the line starts with 'def' (for Python) or 'public' (for Java) or 'function' (for JavaScript)
        elif line.startswith('def') or (language == 'java' and line.strip().startswith('public')) or (
                language == 'javascript' and line.strip().startswith('function')):
            code_lines.append(line)
            inside_function = True
        # Add lines inside class/function definitions
        elif inside_class or inside_function:
            code_lines.append(line)
        # Break if we encounter another 'class' or 'def' line
        elif inside_class or inside_function:
            break

    # Join the import statements, class/function definitions, and other code lines to form the code block
    extracted_code = '\n'.join(import_statements + code_lines)

    extracted_code = extracted_code.strip().replace('```', '')

    return extracted_code


def write_code_to_file(module_path, code, language):
    """
    Write the extracted code into a new file.

    Args:
        module_path (str): The path of the module.
        code (str): The extracted code to be written into the new file.
        language (str): The programming language of the code ('python', 'java', or 'javascript').
    """
    # Extract the directory path and file name from the module path
    directory_path, file_name = os.path.split(module_path)

    # Determine the test directory name based on the language
    test_directory_name = "test"

    test_directory = os.path.join(os.path.dirname(directory_path), test_directory_name)
    if not os.path.exists(test_directory):
        os.makedirs(test_directory)

    # Create a new file path for the test file with the original file name suffixed with "_test"
    test_file_path = os.path.join(test_directory,
                                  file_name[:-3] + "_test.py" if language == 'python' else file_name[
                                                                                           :-5] + "Test.java" if language == 'java' else file_name[
                                                                                                                                         :-3] + "_test.js")

    # Write the extracted code into the new file
    with open(test_file_path, "w") as test_file:
        test_file.write(code)
