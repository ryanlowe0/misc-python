
'''
Refactorings

Create Empty Class 
Add Instance Variable 
Add Method Delete Class
Delete Instance Variable 
Delete Methods 
Rename Class 
Rename Instance Variable
Rename Method
Add Method Argument 
Delete Method Argument
Reorder Method Arguments 
Convert VarRef to Message 
Extract Code as Method
Inline Method
Change Superclass 
Pull Up Instance Variable 
Pull Up Method 
Push Down Instance Variable 
Push Down Method 
Move InstVar into Component 
Move Method into Component

Identify/Delete Commented-out Code

Comments in the middle of a method often point out good places to extract. 
(and can serve as the new method's docstring, and possibly help naming it)


Need to have tests to ensure a refactoring is safe, in general. The plan is to
automate this by tracking inputs and outputs for a variety of inputs. It would
be possible to gauge the risk of a refactoring that actually does change the
behavior slightly, but only outside of the expected parameter range. Also,
extra "safety" code can be added at compile-time, which avoids dirtying up the
code and making it hard to read.




'''

