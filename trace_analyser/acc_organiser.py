class Accelerator:
    def __init__(self, pg, startRow, startCol, accID) -> None:
        self.pg = pg
        self.startRow = startRow
        self.startCol = startCol

# class FreeArea:
#     def __init__(self, startRow, startCol, numRows, numCols) -> None:
#         self.startRow = startRow 
#         self.startCol = startCol
#         self.numRows = numRows
#         self.numCols = numCols
class ReconfigurableFabric:
    def __init__(self, numRows, numCols):
        self.numRows = numRows
        self.numCols = numCols

        self.accelerators = {}
        
        self.slots = []
        for i in range(numRows):
            innerArray = [None] * numCols #m columns
            self.slots.append(innerArray) #n rows

    def addAccelerator(self, startRow, startCol, accID, pg):
        acc = Accelerator(pg, startRow, startCol, accID)
        self.accelerators[accID] = acc

        for i in range(startRow, startRow + pg.n):
            for j in range(startCol, startCol + pg.m):
                self.slots[i][j] = accID

    def removeAccelerator(self, accID):
        acc = self.accelerators[accID]

        for i in range(acc.startRow,acc.startRow + acc.pg.n):
            for j in range(acc.startCol, acc.startCol + acc.pg.m):
                self.slots[i][j] = None

        del self.accelerators[accID]

    def checkIfAccerleratorFits(self, numRows, numCols, startRow, startCol):
        if (startRow + numRows) > self.numRows:
            return False
        
        if (startCol + numCols) > self.numCols:
            return False 

        for i in range(startRow, startRow+numRows):
            for j in range(startCol, startCol+numCols):
                if self.slots[i][j] == None:
                    return False

        return True

    def findFreeSpaceForAcc(self, pg):
        numRows = pg.n
        numCols = pg.m


        for rowNum, row in enumerate(self.slots):
            for colNum, col in row:
                if col == None:
                    acceleratorFits = self.checkIfAccerleratorFits(numRows, numCols, rowNum, colNum)
                    if acceleratorFits:
                        return True, rowNum, colNum
        
        return False, None, None



