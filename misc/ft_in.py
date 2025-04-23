#| Item	        | Documentation Notes                                         |
#|--------------|-------------------------------------------------------------|
#| Filename     | ft-in.py                                                    |
#| EntryPoint   | __main__                                                    |
#| Purpose      | add, subtract, multiply, divide feet and inches             |                   
#| Inputs       | by user                                                     |                                                                         
#| Outputs      | feet result in decimal                                      |                                                           
#| Dependencies |                                                             |                                     
#| By Name,Date | T.Sciple, 11/28/2024                                        |                                                           


def addMissingInchMark(tmpStr3):
    # This function adds a missing inch mark if any number is found following a foot mark
    i=0
    ftPos=0
    numPos=0
    for char in tmpStr3:
        i=i+1
        if char == '\'':
            ftPos=i
    #restart loop now to find last numeric value
    i=0
    for char in tmpStr3:
        i = i + 1
        if char.isdigit():
            numPos=i
    # If the last numeric character found is greater than the ft position then add inch mark
    if numPos > ftPos:
        tmpStr3 = tmpStr3 + '\"'
        return tmpStr3
    return tmpStr3

def getUnits(tmpStr1):
    # determine whether string contains ft+in=3, feet=1, inch=2
    # assume that if a number follows a feet delim then assume the inch mark is missing
    tmpStr1 = addMissingInchMark(tmpStr1)

    if '"' in tmpStr1 and '\'' in tmpStr1:
        return '3'
    if '\'' in tmpStr1:
        return '1'
    if '"' in tmpStr1:
        return '2'

def getNums(tmpStr2):
    # import regex standard library
    import re
    # replace any non digit characters with pipe symbol | including consecutive characters
    regex = r"\D+"
    subst = "|"
    tmpStr2 = re.sub(regex, subst, tmpStr2, 0)
    # remove trailing pipe
    tmpStr2 = tmpStr2.rstrip("|")
    # now Split the string by defined separators
    return tmpStr2.split("|")


def getDecFt(tmpUnits, tmpNums):
    cntNos = len(tmpNums)
    caseSel = tmpUnits + "." + str(cntNos)
    match caseSel:
        case '1.1':  # feet=1 whole number only
            return float(tmpNums[0])
        case '2.1':  # inch=2 + 1 Number - whole number only
            return float(tmpNums[0]) / 12
        case '2.2':  # inch=2 + 2 Numbers indicating fraction only
            return (float(tmpNums[0]) / float(tmpNums[1])) / 12
        case '2.3':  # inch=2 + 3 Numbers - whole number and fraction
            return (float(tmpNums[0]) + float(tmpNums[1]) / float(tmpNums[2])) / 12
        case '3.2':  # both=3 + 2 number components
            return float(tmpNums[0]) + (float(tmpNums[1])) / 12
        case '3.4':
            return float(tmpNums[0]) + (float(tmpNums[1]) + float(tmpNums[2]) / float(tmpNums[3])) / 12


def ftInToDec(ftInStr):
    # This is the main function that starts the sequence of converting feet-inches-fractional string
    # to a decimal numeric value
    # check for operators at first character and remove them
    chkDelim = ftInStr[0] in "\+\-\*\/"
    if chkDelim == True:
        ftInStr = ftInStr[1:]
    units = getUnits(ftInStr)
    ftInLst = getNums(ftInStr)
    return getDecFt(units, ftInLst)

def getFtInFromDecFt(tmpDecFt):
    from fractions import Fraction
    ftPart = int(tmpDecFt)
    inchDec = tmpDecFt % 1 * 12
    inchWhole = int(inchDec)
    inchDecPart = inchDec % 1
    inchfrac = round(inchDecPart*16, 0)/16
    frac = Fraction(inchfrac)
    if ftPart != 0:
        ftInFracStr = str(ftPart)
    else: ftInFracStr = ''
    ftInFracStr = ftInFracStr + '\'' + '-' + str(inchWhole)
    if frac != 0:
        ftInFracStr = ftInFracStr + ' ' + str(frac)
    ftInFracStr = ftInFracStr + '\"'
    return ftInFracStr

def getResult(tmpStr, tmpResult):
    opChoice = tmpStr[0]
    match opChoice:
        case '-':
            decFt = ftInToDec(tmpStr)
            tmpResult = tmpResult - decFt
            return tmpResult
        case '*':
            decFt = ftInToDec(tmpStr)
            tmpResult = tmpResult * decFt
            return tmpResult
        case '/':
            decFt = ftInToDec(tmpStr)
            tmpResult = tmpResult / decFt
            return tmpResult
        case other:
            decFt = ftInToDec(tmpStr)
            tmpResult = tmpResult + decFt
            return tmpResult

if __name__ == "__main__":
    result = 0
    userInp = " "
    print('Enter +-*/ then Ft-In-1/16 Values to Add, Subtract, Multiply or Divide')
    while userInp != "":
        userInp = input('Input : ')
        if userInp != "":
            result = getResult(userInp, result)
        print('Result Dec Ft = ', result, ' ( Ft-In-1/16s = ', getFtInFromDecFt(result), ')')
