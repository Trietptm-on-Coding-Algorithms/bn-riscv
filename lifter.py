# Copyright 2020 Katharina Utz <katharina.utz@stud.uni-due.de>
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from binaryninja import Architecture, LowLevelILLabel

# TODO: make sure all expressions are lifted correctly for risc-v 64-bit


class Lifter:
    def __init__(self, addr_size, arch_name='riscv'):
        self.arch_name = arch_name
        self.addr_size = addr_size

    def lift(self, il, instr, mnemonic):
        """
        main entry point for lifting instruction to LLIL
        """

        if mnemonic == 'or':
            mnemonic = 'or_expr'
        elif mnemonic == 'and':
            mnemonic = 'and_expr'
        elif mnemonic == 'not':
            mnemonic = 'not_expr'

        if hasattr(self, mnemonic):
            getattr(self, mnemonic)(il, instr.op.split(), instr.imm)
        else:
            il.append(il.unimplemented())

    def condBranch(self, il, cond, imm):
        """
        generic helper/lifter for all conditional branches
        """
        dest = il.add(
            self.addr_size, il.const(self.addr_size, il.current_address),
            il.sign_extend(self.addr_size, il.const(self.addr_size, imm)))

        t = il.get_label_for_address(Architecture[self.arch_name],
                                     il.current_address + imm)
        if t is None:
            t = LowLevelILLabel()
            indirect = True
        else:
            indirect = False

        f_label_found = True

        f = il.get_label_for_address(Architecture[self.arch_name],
                                     il.current_address + 4)
        if f is None:
            f = LowLevelILLabel()
            f_label_found = False

        il.append(il.if_expr(cond, t, f))

        if indirect:
            il.mark_label(t)
            il.append(il.jump(dest))

        if not f_label_found:
            il.mark_label(f)

    def jal(self, il, op, imm):

        if len(op) < 1:
            ret_adr = 'ra'
        else:
            ret_adr = op[0]

        label = il.get_label_for_address(Architecture[self.arch_name],
                                         il.current_address + imm)

        if ret_adr != 'zero':
            il.append(
                il.set_reg(self.addr_size, ret_adr,
                           il.const(self.addr_size, il.current_address + 4)))

        if label is not None:
            il.append(il.goto(label))
        else:
            il.append(
                il.call(il.const(self.addr_size, il.current_address + imm)))

    def j(self, il, op, imm):
        op = ['zero']
        self.jal(il, op, imm)

    def jr(self, il, op, imm):
        regs = ['zero', op[0]]
        self.jalr(il, regs, imm)

    def jalr(self, il, op, imm):

        if len(op) < 2:
            ret_adr = 'ra'
            base = op[0]
        else:
            ret_adr = op[0]
            base = op[1]

        target = il.and_expr(
            self.addr_size,
            il.add(self.addr_size, il.reg(self.addr_size, base),
                   il.const(self.addr_size, imm)),
            il.neg_expr(self.addr_size, il.const(self.addr_size, 2)))

        if ret_adr != 'zero':
            il.append(
                il.set_reg(self.addr_size, ret_adr,
                           il.const(self.addr_size, il.current_address + 4)))

        il.append(il.call(target))

    def ret(self, il, op, imm):
        il.append(
            il.ret(
                il.and_expr(
                    self.addr_size, il.reg(self.addr_size, 'ra'),
                    il.neg_expr(self.addr_size, il.const(self.addr_size, 2)))))
        il.append(il.pop(self.addr_size))

    def beq(self, il, op, imm):
        cond = il.compare_equal(self.addr_size, il.reg(self.addr_size, op[0]),
                                il.reg(self.addr_size, op[1]))
        self.condBranch(il, cond, imm)

    def beqz(self, il, op, imm):
        cond = il.compare_equal(self.addr_size, il.reg(self.addr_size, op[0]),
                                il.const(self.addr_size, 0))
        self.condBranch(il, cond, imm)

    def bne(self, il, op, imm):
        cond = il.compare_not_equal(self.addr_size,
                                    il.reg(self.addr_size, op[0]),
                                    il.reg(self.addr_size, op[1]))
        self.condBranch(il, cond, imm)

    def bnez(self, il, op, imm):
        cond = il.compare_not_equal(self.addr_size,
                                    il.reg(self.addr_size, op[0]),
                                    il.const(self.addr_size, 0))
        self.condBranch(il, cond, imm)

    def blt(self, il, op, imm):
        cond = il.compare_signed_less_than(self.addr_size,
                                           il.reg(self.addr_size, op[0]),
                                           il.reg(self.addr_size, op[1]))
        self.condBranch(il, cond, imm)

    def bltu(self, il, op, imm):
        cond = il.compare_unsigned_less_than(self.addr_size,
                                             il.reg(self.addr_size, op[0]),
                                             il.reg(self.addr_size, op[1]))
        self.condBranch(il, cond, imm)

    def bltz(self, il, op, imm):
        cond = il.compare_signed_less_than(self.addr_size,
                                           il.reg(self.addr_size, op[0]),
                                           il.const(self.addr_size, 0))
        self.condBranch(il, cond, imm)

    def bgtz(self, il, op, imm):
        cond = il.compare_signed_less_than(self.addr_size,
                                           il.const(self.addr_size, 0),
                                           il.reg(self.addr_size, op[0]))
        self.condBranch(il, cond, imm)

    def bge(self, il, op, imm):
        cond = il.compare_signed_greater_equal(self.addr_size,
                                               il.reg(self.addr_size, op[0]),
                                               il.reg(self.addr_size, op[1]))
        self.condBranch(il, cond, imm)

    def bgeu(self, il, op, imm):
        cond = il.compare_unsigned_greater_equal(self.addr_size,
                                                 il.reg(self.addr_size, op[0]),
                                                 il.reg(self.addr_size, op[0]))
        self.condBranch(il, cond, imm)

    def blez(self, il, op, imm):
        cond = il.compare_signed_greater_equal(self.addr_size,
                                               il.const(self.addr_size, 0),
                                               il.reg(self.addr_size, op[0]))
        self.condBranch(il, cond, imm)

    def bgez(self, il, op, imm):
        cond = il.compare_unsigned_greater_equal(self.addr_size,
                                                 il.reg(self.addr_size, op[0]),
                                                 il.const(self.addr_size, 0))
        self.condBranch(il, cond, imm)

    def add(self, il, op, imm):
        il.append(
            il.set_reg(
                self.addr_size, op[0],
                il.add(self.addr_size, il.reg(self.addr_size, op[1]),
                       il.reg(self.addr_size, op[2]))))

    def addi(self, il, op, imm):
        il.append(
            il.set_reg(
                self.addr_size, op[0],
                il.add(self.addr_size, il.reg(self.addr_size, op[1]),
                       il.const(self.addr_size, imm))))

    def sub(self, il, op, imm):
        il.append(
            il.set_reg(
                self.addr_size, op[0],
                il.sub(self.addr_size, il.reg(self.addr_size, op[1]),
                       il.reg(self.addr_size, op[2]))))

    def neg(self, il, op, imm):
        il.append(
            il.set_reg(
                self.addr_size, op[0],
                il.neg_expr(self.addr_size, il.reg(self.addr_size, op[1]))))

    def not_expr(self, il, op, imm):
        il.append(
            il.set_reg(
                self.addr_size, op[0],
                il.not_expr(self.addr_size, il.reg(self.addr_size, op[1]))))

    def mul(self, il, op, imm):
        il.append(
            il.set_reg(
                self.addr_size, op[0],
                il.mult(self.addr_size, il.reg(self.addr_size, op[1]),
                        il.reg(self.addr_size, op[2]))))

    def div(self, il, op, imm):
        il.append(
            il.set_reg(
                self.addr_size, op[0],
                il.div_signed(self.addr_size, il.reg(self.addr_size, op[1]),
                              il.reg(self.addr_size, op[2]))))

    def divu(self, il, op, imm):
        il.append(
            il.set_reg(
                self.addr_size, op[0],
                il.div_unsigned(self.addr_size, il.reg(self.addr_size, op[1]),
                                il.reg(self.addr_size, op[2]))))

    def mod(self, il, op, imm):
        il.append(
            il.set_reg(
                self.addr_size, op[0],
                il.mod_signed(self.addr_size, il.reg(self.addr_size, op[1]),
                              il.reg(self.addr_size, op[2]))))

    def modu(self, il, op, imm):
        il.append(
            il.set_reg(
                self.addr_size, op[0],
                il.mod_unsigned(self.addr_size, il.reg(self.addr_size, op[1]),
                                il.reg(self.addr_size, op[2]))))

    def and_expr(self, il, op, imm):
        il.append(
            il.set_reg(
                self.addr_size, op[0],
                il.and_expr(self.addr_size, il.reg(self.addr_size, op[1]),
                            il.reg(self.addr_size, op[2]))))

    def andi(self, il, op, imm):
        il.append(
            il.set_reg(
                self.addr_size, op[0],
                il.and_expr(
                    self.addr_size, il.reg(self.addr_size, op[1]),
                    il.sign_extend(
                        self.addr_size,
                        il.and_expr(2, il.const(2, imm), il.const(2,
                                                                  0xfff))))))

    def or_expr(self, il, op, imm):
        il.append(
            il.set_reg(
                self.addr_size, op[0],
                il.or_expr(self.addr_size, il.reg(self.addr_size, op[1]),
                           il.reg(self.addr_size, op[2]))))

    def ori(self, il, op, imm):
        il.append(
            il.set_reg(
                self.addr_size, op[0],
                il.or_expr(
                    self.addr_size, il.reg(self.addr_size, op[1]),
                    il.sign_extend(
                        self.addr_size,
                        il.and_expr(2, il.const(2, imm), il.const(2,
                                                                  0xfff))))))

    def xor(self, il, op, imm):
        il.append(
            il.set_reg(
                self.addr_size, op[0],
                il.xor_expr(self.addr_size, il.reg(self.addr_size, op[1]),
                            il.reg(self.addr_size, op[2]))))

    def xori(self, il, op, imm):
        il.append(
            il.set_reg(
                self.addr_size, op[0],
                il.xor_expr(
                    self.addr_size, il.reg(self.addr_size, op[1]),
                    il.sign_extend(
                        self.addr_size,
                        il.and_expr(2, il.const(2, imm), il.const(2,
                                                                  0xfff))))))

    def sll(self, il, op, imm):
        il.append(
            il.set_reg(
                self.addr_size, op[0],
                il.shift_left(self.addr_size, il.reg(self.addr_size, op[1]),
                              il.reg(self.addr_size, op[2]))))

    def slli(self, il, op, imm):
        il.append(
            il.set_reg(
                self.addr_size, op[0],
                il.shift_left(
                    self.addr_size, il.reg(self.addr_size, op[1]),
                    il.and_expr(1, il.const(1, imm), il.const(1, 0xf)))))

    def srl(self, il, op, imm):
        il.append(
            il.set_reg(
                self.addr_size, op[0],
                il.logical_shift_right(self.addr_size,
                                       il.reg(self.addr_size, op[1]),
                                       il.reg(self.addr_size, op[2]))))

    def srli(self, il, op, imm):
        il.append(
            il.set_reg(
                self.addr_size, op[0],
                il.logical_shift_right(
                    self.addr_size, il.reg(self.addr_size, op[1]),
                    il.and_expr(1, il.const(1, imm), il.const(1, 0xf)))))

    def sra(self, il, op, imm):
        il.append(
            il.set_reg(
                self.addr_size, op[0],
                il.arith_shift_right(self.addr_size,
                                     il.reg(self.addr_size, op[1]),
                                     il.reg(self.addr_size, op[2]))))

    def srai(self, il, op, imm):
        il.append(
            il.set_reg(
                self.addr_size, op[0],
                il.arith_shift_right(self.addr_size,
                                     il.reg(self.addr_size, op[1]),
                                     il.const(self.addr_size, imm))))

    def lui(self, il, op, imm):
        il.append(
            il.set_reg(
                self.addr_size,
                op[0],
                # il.shift_left(self.addr_size,
                #               il.zero_extend(self.addr_size, il.const(3, imm)),
                #               # il.const(self.addr_size, imm)),
                #               il.const(self.addr_size, 12))
                il.const(self.addr_size, imm << 12)))

    def auipc(self, il, op, imm):
        il.append(
            il.set_reg(
                self.addr_size, op[0],
                il.add(
                    self.addr_size, il.reg(self.addr_size, 'pc'),
                    il.zero_extend(
                        self.addr_size,
                        il.and_expr(3, il.const(3, imm), il.const(3,
                                                                  0xfffff))))))

    def sw(self, il, op, imm):
        offset = il.add(self.addr_size, il.reg(self.addr_size, op[1]),
                        il.const(self.addr_size, imm))
        il.append(
            il.store(self.addr_size, offset, il.reg(self.addr_size, op[0])))

    def sh(self, il, op, imm):
        offset = il.add(self.addr_size, il.reg(self.addr_size, op[1]),
                        il.const(2, imm))
        il.append(
            il.store(self.addr_size, offset, il.reg(self.addr_size, op[0])))

    def sb(self, il, op, imm):
        offset = il.add(self.addr_size, il.reg(self.addr_size, op[1]),
                        il.const(1, imm))
        il.append(
            il.store(self.addr_size, offset, il.reg(self.addr_size, op[0])))

    def lb(self, il, op, imm):
        offset = il.add(self.addr_size, il.reg(self.addr_size, op[1]),
                        il.sign_extend(2, il.const(1, imm)))
        il.append(il.set_reg(self.addr_size, op[0], il.load(1, offset)))

    def lbu(self, il, op, imm):
        offset = il.add(self.addr_size, il.reg(self.addr_size, op[1]),
                        il.sign_extend(2, il.const(1, imm)))
        il.append(
            il.set_reg(self.addr_size, op[0],
                       il.zero_extend(self.addr_size, il.load(1, offset))))

    def lh(self, il, op, imm):
        offset = il.add(self.addr_size, il.reg(self.addr_size, op[1]),
                        il.sign_extend(2, il.const(2, imm)))
        il.append(il.set_reg(self.addr_size, op[0], il.load(2, offset)))

    def lhu(self, il, op, imm):
        offset = il.add(self.addr_size, il.reg(self.addr_size, op[1]),
                        il.zero_extend(22, il.const(2, imm)))
        il.append(
            il.set_reg(self.addr_size, op[0],
                       il.zero_extend(self.addr_size, il.load(16, offset))))

    def lw(self, il, op, imm):
        offset = il.add(self.addr_size, il.reg(self.addr_size, op[1]),
                        il.const(self.addr_size, imm))
        il.append(
            il.set_reg(self.addr_size, op[0], il.load(self.addr_size, offset)))

    def mv(self, il, op, imm):

        if op[1] == 'zero':
            il.append(
                il.set_reg(self.addr_size, op[0], il.const(self.addr_size, 0)))
        else:
            il.append(
                il.set_reg(self.addr_size, op[0],
                           il.reg(self.addr_size, op[1])))

    def slt(self, il, op, imm):
        il.append(
            il.set_reg(
                self.addr_size, op[0],
                il.compare_signed_less_than(self.addr_size,
                                            il.reg(self.addr_size, op[1]),
                                            il.reg(self.addr_size, op[2]))))

    def sltu(self, il, op, imm):
        il.append(
            il.set_reg(
                self.addr_size, op[0],
                il.compare_unsigned_less_than(self.addr_size,
                                              il.reg(self.addr_size, op[1]),
                                              il.reg(self.addr_size, op[2]))))

    def slti(self, il, op, imm):
        il.append(
            il.set_reg(
                self.addr_size, op[0],
                il.compare_signed_less_than(self.addr_size,
                                            il.reg(self.addr_size, op[1]),
                                            il.const(self.addr_size, imm))))

    def sltiu(self, il, op, imm):
        il.append(
            il.set_reg(
                self.addr_size, op[0],
                il.compare_unsigned_less_than(self.addr_size,
                                              il.reg(self.addr_size, op[1]),
                                              il.const(self.addr_size, imm))))

    def ecall(self, il, op, imm):
        il.append(il.system_call())

    def ebreak(self, il, op, imm):
        il.append(il.breakpoint())

    def nop(self, il, op, imm):
        il.append(il.nop())
